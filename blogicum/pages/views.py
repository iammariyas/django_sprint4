from django.shortcuts import render


# Create your views here.
def csrf_failure(request, reason=''):
    return render(request, 'pages/403csrf.html', status=403)


def page_not_found(request, exception):
    return render(request, 'pages/404.html', status=404)

def internal_server_error(request):
    return render(request, 'pages/500.html', status=500)
