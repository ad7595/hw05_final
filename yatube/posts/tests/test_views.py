from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.conf import settings

from posts.models import Group, Post, Comment, Follow

import shutil
import tempfile

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='image.jpg',
            content=cls.image,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            image=cls.uploaded,
        )
        cls.comment = Comment.objects.create(
            post=cls.post, author=cls.user, text='Тестовый комментарий'
        )
        cls.post_with_group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост с указанием группы',
            group=cls.group,
        )
        cls.new_group = Group.objects.create(
            title='Пустая группа',
            slug='empty-group',
            description='Тестовое описание пустой группы',
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.user)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='TestUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.user_not_author = User.objects.create_user(username='NotAuth')
        self.not_author_client = Client()
        self.not_author_client.force_login(self.user_not_author)
        cache.clear()

    def test_pages_uses_correct_templates(self):
        """URL-адрес использует соответствующий шаблон"""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': 'auth'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index с соответствующим контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn(self.post, response.context['page_obj'])

    def test_group_list_show_correct_context(self):
        """Шаблон group_list с соответствующим контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertIn('group', response.context)
        self.assertEqual(response.context['group'], self.group)
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.filter(group__slug='test-slug').count()
        )

    def test_profile_show_correct_context(self):
        """Шаблон profile с соответствующим контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        self.assertIn('author', response.context)
        self.assertEqual(response.context['author'], self.post.author)
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.filter(author__username='auth').count()
        )

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{self.post.id}'}
            )
        )
        self.assertEqual(response.context['post'], self.post)
        self.assertIn(self.comment, response.context['comments'])
        self.assertIn('form', response.context)
        self.assertEqual(len(response.context['comments']), 1)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create с соответствующим контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = (
                    response.context.get('form').fields.get(value)
                )
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit с соответствующим контекстом."""
        response = self.author_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.id}'}
            )
        )
        self.assertTrue(response.context['is_edit'])

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = (
                    response.context.get('form').fields.get(value)
                )
                self.assertIsInstance(form_field, expected)

    def test_new_post_with_group_checking(self):
        """При создании поста с выбором группы, пост отображается
        на главной странице, в группе и в профайле."""
        reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'auth'})
        )
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertIn(
                    self.post_with_group,
                    response.context['page_obj']
                )

    def test_post_with_group_not_in_new_group(self):
        """Post_with_group не попал в группу, для которой
        не был предназначен."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': 'empty-group'})
        )
        self.assertEqual(len(response.context['page_obj']), 0)


class PaginatorViewsTests(TestCase):

    POSTS_NUMBERS_ON_SECOND_PAGE = 3
    POSTS_NUMBERS = 13
    NUMBER_OF_POSTS = 10

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        for num in range(cls.POSTS_NUMBERS):
            cls.post = Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост {num}',
                group=cls.group,
            )
        cls.author_client = Client()
        cls.author_client.force_login(cls.user)

    def setUp(self):
        self.guest_client = Client()
        cache.clear()

    def test_first_pages_contains_ten_records(self):
        """Число постов на первых страницах главной,
        в группе и в профайле равно NUMBER_OF_POSTS."""
        reverse_names = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'auth'})
        )

        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.NUMBER_OF_POSTS
                )

    def test_second_pages_contains_three_records(self):
        """Количество постов на вторых страницах главной,
        в группе и в профайле равно POSTS_NUMBERS_ON_SECOND_PAGE."""
        reverse_names = (
            (reverse('posts:index') + '?page=2'),
            (
                reverse(
                    'posts:group_list',
                    kwargs={'slug': 'test-slug'}
                ) + '?page=2'
            ),
            (reverse('posts:profile', kwargs={'username': 'auth'}) + '?page=2')
        )

        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']),
                    self.POSTS_NUMBERS_ON_SECOND_PAGE
                )


User = get_user_model()


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post = Post.objects.create(
            author=User.objects.create_user(username='test_user'),
            text='Тестовый текст поста кэш')

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='test_user1')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_cache_index(self):
        """Тест кэширования страницы index.html"""
        state_1 = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(pk=1)
        post_1.text = 'Измененный текст кэш'
        post_1.save()
        state_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(state_1.content, state_2.content)
        cache.clear()
        state_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(state_1.content, state_3.content)


class FollowTests(TestCase):
    """Тесты проверки работы механизма подписки на авторов"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.follower = User.objects.create_user(username='follower')
        cls.following = User.objects.create_user(username='following')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.following,
        )

    def setUp(self):
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_following = Client()
        self.authorized_following.force_login(self.following)
        cache.clear()

    def test_auth_user_can_follow_author(self):
        """Тест проверяющий что авторизованный пользователь
        может подписываться на других"""
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower, author=self.following
            ).exists()
        )
        self.authorized_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.following.username},
            )
        )
        self.assertEqual(Follow.objects.count(), 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.follower, author=self.following
            ).exists()
        )

    def test_auth_user_can_unfollow_author(self):
        """Тест проверяющий что авторизованный пользователь
        может отписаться от автора"""
        Follow.objects.create(user=self.follower, author=self.following)
        self.authorized_follower.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.following.username},
            )
        )
        self.assertEqual(Follow.objects.count(), 0)
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower, author=self.following
            ).exists()
        )

    def test_subscription_feed_for_auth_users(self):
        """Запись публикуется в ленте подписчиков автора"""
        Follow.objects.create(user=self.follower, author=self.following)
        response = self.authorized_follower.get('/follow/')
        follower_index = response.context['page_obj'][0]
        self.assertEqual(self.post, follower_index)
