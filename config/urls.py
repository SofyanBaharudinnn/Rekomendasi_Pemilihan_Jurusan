# pyrefly: ignore [missing-import]
# pyrefly: ignore [missing-import]
from django.urls import path
# pyrefly: ignore [missing-import]
from django.conf import settings
# pyrefly: ignore [missing-import]
from django.conf.urls.static import static
from rekomendasi import views

urlpatterns = [
    # ── Halaman publik ────────────────────────────────────────────
    path('', views.index, name='index'),

    # ── Auth ──────────────────────────────────────────────────────
    path('login/',    views.login_view,    name='login'),
    path('logout/',   views.logout_view,   name='logout'),
    path('register/', views.register_view, name='register'),

    # ── Dashboard ─────────────────────────────────────────────────
    path('dashboard/',       views.dashboard_user,  name='dashboard_user'),
    path('admin-dashboard/', views.dashboard_admin, name='dashboard_admin'),

    # ── Predict API ───────────────────────────────────────────────
    path('predict/', views.predict, name='predict'),

    # ── Print / PDF hasil ─────────────────────────────────────────
    path('user/export/<int:hasil_id>/', views.api_user_export_pdf, name='api_user_export_pdf'),

    # ── User API: Profil & Gamifikasi ─────────────────────────────
    path('api/user/profile/',         views.api_user_profile,        name='api_user_profile'),
    path('api/user/profile/update/',  views.api_user_profile_update, name='api_user_profile_update'),
    path('api/user/avatar/',          views.api_user_avatar,         name='api_user_avatar'),
    path('api/user/badges/',          views.api_user_badges,         name='api_user_badges'),

    # ── User API: Tes & Riwayat ───────────────────────────────────
    path('api/user/riwayat/', views.api_user_riwayat, name='api_user_riwayat'),
    path('api/user/feedback/', views.api_user_feedback, name='api_user_feedback'),

    # ── User API: Informatif ──────────────────────────────────────
    path('api/user/jurusan/',              views.api_jurusan_list_user,   name='api_jurusan_list_user'),

    path('api/user/jurusan/<str:nama>/',   views.api_jurusan_detail_user, name='api_jurusan_detail_user'),
    path('api/user/kalkulator/',           views.api_kalkulator_ptn,      name='api_kalkulator_ptn'),
    path('api/user/artikel/',              views.api_user_artikel,        name='api_user_artikel'),
    path('api/user/faq/',                  views.api_user_faq,            name='api_user_faq'),

    # ── Admin API: Dashboard Stats ────────────────────────────────
    path('api/admin/stats/', views.api_dashboard_stats, name='api_dashboard_stats'),

    # ── Admin API: User Management ────────────────────────────────
    path('api/admin/users/',                        views.api_users_list,   name='api_users_list'),
    path('api/admin/users/export/',                 views.api_export_users, name='api_export_users'),
    path('api/admin/users/<int:user_id>/toggle/',   views.api_user_toggle,  name='api_user_toggle'),
    path('api/admin/users/<int:user_id>/',          views.api_admin_user_detail, name='api_admin_user_detail'),

    # ── Admin API: Konten ─────────────────────────────────────────
    path('api/admin/jurusan/',                   views.api_jurusan_list,   name='api_jurusan_list'),
    path('api/admin/jurusan/<int:jurusan_id>/',  views.api_jurusan_detail, name='api_jurusan_detail'),
    path('api/admin/artikel/',                   views.api_artikel_list,   name='api_artikel_list'),
    path('api/admin/artikel/<int:artikel_id>/',  views.api_artikel_detail, name='api_artikel_detail'),
    path('api/admin/faq/',                       views.api_faq_list,       name='api_faq_list'),
    path('api/admin/faq/<int:faq_id>/',          views.api_faq_detail,     name='api_faq_detail'),

    # ── Admin API: Analitik ───────────────────────────────────────
    path('api/admin/analytics/',       views.api_analytics,      name='api_analytics'),
    path('api/admin/export/laporan/',  views.api_export_laporan,  name='api_export_laporan'),

    # ── Admin API: Model ML ───────────────────────────────────────
    path('api/admin/ml/status/',  views.api_ml_status,  name='api_ml_status'),
    path('api/admin/ml/retrain/', views.api_ml_retrain, name='api_ml_retrain'),
    path('api/admin/ml/upload/',  views.api_ml_upload,  name='api_ml_upload'),

    # ── Testimoni & Forum API ─────────────────────────────────────────
    path('api/testimoni/', views.api_testimoni, name='api_testimoni'),
    path('api/forum/', views.api_forum_list, name='api_forum_list'),
    path('api/forum/<int:post_id>/', views.api_forum_detail, name='api_forum_detail'),
    path('api/forum/<int:post_id>/comment/', views.api_forum_comment, name='api_forum_comment'),
    path('api/similar-users/', views.api_similar_users, name='api_similar_users'),

    # ── WhatsApp Share ─────────────────────────────────────────────────
    path('api/user/share/whatsapp/<int:hasil_id>/', views.api_share_whatsapp, name='api_share_whatsapp'),

    # ── Admin API: Activity Log ────────────────────────────────────────
    path('api/admin/activity-log/',        views.api_activity_log,       name='api_activity_log'),
    path('api/admin/activity-log/clear/',  views.api_activity_log_clear, name='api_activity_log_clear'),

    # ── Kontak (Hubungi Kami) API ──────────────────────────────────────
    path('api/kontak/submit/', views.api_kontak_submit, name='api_kontak_submit'),
    path('api/admin/pesan/', views.api_admin_pesan_list, name='api_admin_pesan_list'),
    path('api/admin/pesan/<int:pesan_id>/delete/', views.api_admin_pesan_delete, name='api_admin_pesan_delete'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)