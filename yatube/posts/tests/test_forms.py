from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings

from posts.forms import PostForm
from posts.models import Group, Post, Comment

import tempfile
import shutil

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.author_client = Client()
        cls.author_client.force_login(cls.user)
        cls.form = PostForm()
        cls.comment = 'Тестовый комментарий'

    def setUp(self):
        self.user = User.objects.create_user(username='TestUser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.guest_client = Client()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create(self):
        """При отправке валидной формы со страницы
        создания поста, создается запись в БД."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user
            ).exists()
        )

    def test_post_create_with_image(self):
        """При отправке валидной формы со страницы
        создания поста с картинкой, создается запись в БД."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
            'group': self.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
                author=self.user,
                image='posts/small.gif'
            ).exists()
        )

    def test_post_edit(self):
        """При отправке валидной формы со страницы
        редактирования поста, происходит изменение записи в БД."""
        form_data = {
            'text': 'Новый текст. Отредактировано',
            'group': self.group.id,
        }
        response = self.author_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post.id,)
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(self.post.id,)
            )
        )
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=form_data['text'],
                group=form_data['group'],
                author=self.post.author,
                pub_date=self.post.pub_date
            ).exists()
        )

    def test_labels(self):
        """Проверяем поля labels."""
        text_label = PostFormTests.form.fields['text'].label
        group_label = PostFormTests.form.fields['group'].label
        image_label = PostFormTests.form.fields['image'].label
        self.assertEqual(text_label, 'Текст поста')
        self.assertEqual(group_label, 'Группа')
        self.assertEqual(image_label, 'Картинка')

    def test_help_texts(self):
        """Проверяем поля help_texts."""
        text_help_text = PostFormTests.form.fields['text'].help_text
        group_help_text = PostFormTests.form.fields['group'].help_text
        image_help_text = PostFormTests.form.fields['image'].help_text
        self.assertEqual(text_help_text, 'Текст нового поста')
        self.assertEqual(
            group_help_text,
            'Группа, к которой будет относиться пост'
        )
        self.assertEqual(image_help_text, 'Картинка для поста')

    def test_post_edit_not_auth(self):
        """ При запросе неавторизованного пользователя пост не будет
        отредактирован."""
        form_data = {
            'text': 'Новый текст. Отредактировано',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post.id,)
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/posts/1/edit/')
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=self.post.text,
                group=self.post.group,
                author=self.post.author,
                pub_date=self.post.pub_date
            ).exists()
        )

    def test_post_create_not_auth_posts_count(self):
        """ Попытка не авторизованного пользователя редактировать пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(posts_count, Post.objects.count())
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_not_author(self):
        """ Попытка не автора поста отредактировать пост."""
        form_data = {
            'text': 'Новый текст. Отредактировано',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post.id,)
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/posts/1/')
        self.assertTrue(
            Post.objects.filter(
                id=self.post.id,
                text=self.post.text,
                group=self.post.group,
                author=self.post.author,
                pub_date=self.post.pub_date
            ).exists()
        )

    def test_post_create_no_group(self):
        """Создание нового поста без указания группы."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Новый текст',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group__isnull=True,
                author=self.user
            ).exists()
        )

    def test_add_comments_post_authorized(self):
        """Аавторизованный пользователь и автор создает комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': self.comment,
        }
        response = self.authorized_client.post((
            reverse('posts:add_comment', kwargs={'post_id': self.post.id})),
            data=form_data,
            follow=True
        )
        comment = Comment.objects.last()
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(comment.text, self.comment)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.user)

    def test_add_comments_post_anonymous(self):
        """Анонимный пользоветель создает комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.guest_client.post((
            reverse('posts:add_comment', kwargs={'post_id': self.post.id})),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.id}/comment/')
