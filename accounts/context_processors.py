from .models import TeacherProfile, ParentProfile


def profile_picture(request):
    """Context processor to add current user's profile picture URL (if any) as `user_profile_picture`."""
    url = None
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        try:
            tp = TeacherProfile.objects.filter(user=user).first()
            if tp and tp.profile_picture:
                url = tp.profile_picture.url
        except Exception:
            url = None
        if not url:
            try:
                pp = ParentProfile.objects.filter(user=user).first()
                if pp and pp.profile_picture:
                    url = pp.profile_picture.url
            except Exception:
                url = None
    return {'user_profile_picture': url}
