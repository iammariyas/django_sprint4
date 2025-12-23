from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.views.generic import ListView
from django.views.generic import DetailView
from django.views.generic.edit import FormMixin

from .forms import PostForm, CommentForm, UserForm
from .models import Post, Category, Comment


# Create your views here.
User = get_user_model()


def get_posts_with_comments():
    return (
        Post.objects.select_related('category', 'location', 'author')
        .filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )


def get_paginator(request, queryset, num_pages=10):
    paginator = Paginator(queryset, num_pages)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


class IndexView(ListView):
    model = Post
    template_name = 'blog/index.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        return get_posts_with_comments()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = self.get_queryset()
        page_obj = get_paginator(self.request, posts, self.paginate_by)
        context['page_obj'] = page_obj
        return context


class PostDetailView(FormMixin, DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    form_class = CommentForm
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)
        if self.request.user != post.author:
            post = get_object_or_404(
                Post,
                id=post.id,
                is_published=True,
                category__is_published=True,
                pub_date__lte=timezone.now(),
            )
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        comments = Comment.objects.select_related('author').filter(post=post)
        context['comments'] = comments
        return context

    def post(self, request):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = self.object
            comment.save()
            return redirect('blog:post_detail', post_id=self.object.id)
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class CategoryPostsView(ListView):
    model = Post
    template_name = 'blog/category.html'
    context_object_name = 'page_obj'

    def get_category(self):
        return get_object_or_404(
            Category, slug=self.kwargs['category_slug'], is_published=True
        )

    def get_queryset(self):
        self.category = self.get_category()
        return get_posts_with_comments().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts = self.get_queryset()
        page_obj = get_paginator(self.request, posts, 10)
        context['page_obj'] = page_obj
        context['category'] = self.get_category()
        return context


@login_required
def create_post(request):
    template = 'blog/create.html'
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', request.user)
    context = {"form": form}
    return render(request, template, context)


@login_required
def edit_post(request, post_id):
    template = 'blog/create.html'
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id)
    form = PostForm(request.POST or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'form': form}
    return render(request, template, context)


@login_required
def delete_post(request, post_id):
    template = 'blog/create.html'
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(request.POST or None, instance=post)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    context = {'form': form}
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    template = 'blog/comment.html'
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id)
    context = {'comment': comment, 'form': form}
    return render(request, template, context)


@login_required
def delete_comment(request, post_id, comment_id):
    template = 'blog/comment.html'
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.author:
        return redirect('blog:post_detail', post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id)
    context = {'comment': comment}
    return render(request, template, context)


def profile(request, username):
    template = 'blog/profile.html'
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.select_related('category', 'location', 'author')
    if request.user == profile_user:
        posts = posts.filter(author=profile_user)
    else:
        posts = posts.filter(
            author=profile_user,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now(),
        )
    posts = posts.annotate(comment_count=Count('comments')).order_by('-pub_date')
    page_obj = get_paginator(request, posts)
    context = {'profile': profile_user, 'page_obj': page_obj}
    return render(request, template, context)


@login_required
def edit_profile(request):
    template = 'blog/user.html'
    form = UserForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    context = {'form': form}
    return render(request, template, context)
