# pyrefly: ignore [missing-import]
from django.shortcuts import render, redirect, get_object_or_404
# pyrefly: ignore [missing-import]
from django.http import JsonResponse, HttpResponse
# pyrefly: ignore [missing-import]
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
# pyrefly: ignore [missing-import]
from django.contrib.auth.decorators import login_required
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.contrib import messages
# pyrefly: ignore [missing-import]
from django.views.decorators.http import require_http_methods, require_POST
# pyrefly: ignore [missing-import]
from django.utils import timezone
# pyrefly: ignore [missing-import]
from django.db.models import Count, Avg, Q
# pyrefly: ignore [missing-import]
from django.conf import settings as django_settings
from functools import wraps
from .models import (HasilRekomendasi, JurusanInfo, JurusanDetail,
                     Artikel, FAQ, ModelVersion,
                     ProfilSiswa, UserBadge, RiwayatPoin,
                     Testimoni, ForumPost, ForumComment, AktivitasLog, PesanKontak,
                     ChatSession, ChatMessage)
from .security import (
    generate_captcha, validate_captcha, set_captcha_session,
    log_activity,
    get_cached_prediction, set_cached_prediction, invalidate_prediction_cache,
)
import json, os, csv, subprocess, sys
# pyrefly: ignore [missing-import]
import numpy as np
from datetime import timedelta, datetime
from collections import defaultdict
import urllib.parse

# ═══════════════════════════════════════════════════════════════════════════════
#  KONSTANTA
# ═══════════════════════════════════════════════════════════════════════════════
JURUSAN_INFO_DEFAULT = {
    'Teknik Informatika': {'icon':'💻','deskripsi':'Cocok untuk yang suka logika, coding, dan teknologi.','prospek':['Software Engineer','Data Scientist','Cybersecurity']},
    'Kedokteran':         {'icon':'🩺','deskripsi':'Ideal untuk jiwa yang peduli kesehatan dan suka ilmu alam.','prospek':['Dokter Umum','Spesialis','Peneliti Medis']},
    'Manajemen':          {'icon':'📊','deskripsi':'Tepat untuk yang suka strategi bisnis dan kepemimpinan.','prospek':['Manajer','Konsultan','Entrepreneur']},
    'Sastra':             {'icon':'📚','deskripsi':'Untuk jiwa kreatif yang mencintai bahasa dan budaya.','prospek':['Penulis','Penerjemah','Jurnalis']},
    'Akuntansi':          {'icon':'🧾','deskripsi':'Cocok untuk yang teliti, suka angka dan keuangan.','prospek':['Akuntan','Auditor','Analis Keuangan']},
    'Biologi':            {'icon':'🔬','deskripsi':'Untuk pecinta alam, lingkungan, dan ilmu kehidupan.','prospek':['Peneliti','Farmasis','Ahli Lingkungan']},
    'Pendidikan':         {'icon':'🎓','deskripsi':'Panggilan jiwa untuk mencerdaskan generasi bangsa.','prospek':['Guru','Dosen','Konselor Pendidikan']},
}

ALL_BADGES = [
    {'key':'pemula',         'label':'🧪 Pemula',          'desc':'Menyelesaikan tes pertama'},
    {'key':'rajin',          'label':'🔁 Rajin Tes',        'desc':'Menyelesaikan 3 kali tes'},
    {'key':'expert',         'label':'🏆 Expert',           'desc':'Menyelesaikan 10 kali tes'},
    {'key':'profil_lengkap', 'label':'📋 Profil Lengkap',   'desc':'Mengisi semua field profil'},
    {'key':'poin_100',       'label':'⭐ Poin 100',          'desc':'Mengumpulkan 100 poin'},
    {'key':'pembaca',        'label':'📰 Pembaca',           'desc':'Membuka halaman artikel'},
    {'key':'explorer',       'label':'🔍 Penjelajah',        'desc':'Melihat detail jurusan'},
]

def get_jurusan_info():
    qs = JurusanInfo.objects.filter(is_active=True)
    if qs.exists():
        return {j.nama: {'icon': j.icon, 'deskripsi': j.deskripsi, 'prospek': j.prospek} for j in qs}
    return JURUSAN_INFO_DEFAULT

# ═══════════════════════════════════════════════════════════════════════════════
#  DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════
def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'error': 'Admin only'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped

def user_api_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped

# ═══════════════════════════════════════════════════════════════════════════════
#  GAMIFIKASI HELPER
# ═══════════════════════════════════════════════════════════════════════════════
def cek_dan_beri_badge(user, badge_key, profil=None):
    """Beri badge jika belum punya. Return True jika baru diraih."""
    if not UserBadge.objects.filter(user=user, badge=badge_key).exists():
        UserBadge.objects.create(user=user, badge=badge_key)
        return True
    return False

def proses_gamifikasi_setelah_tes(user):
    """Proses badge & poin setelah user menyelesaikan tes."""
    profil, _ = ProfilSiswa.objects.get_or_create(user=user)
    total_tes = HasilRekomendasi.objects.filter(user=user).count()

    # Poin +10 per tes
    profil.tambah_poin(10, 'Menyelesaikan tes rekomendasi')

    # Badge berdasarkan jumlah tes
    if total_tes >= 1:  cek_dan_beri_badge(user, 'pemula')
    if total_tes >= 3:  cek_dan_beri_badge(user, 'rajin')
    if total_tes >= 10: cek_dan_beri_badge(user, 'expert')

    # Badge poin
    if profil.poin >= 100: cek_dan_beri_badge(user, 'poin_100')

    # Badge profil lengkap
    if profil.kelengkapan_persen() == 100:
        cek_dan_beri_badge(user, 'profil_lengkap')

# ═══════════════════════════════════════════════════════════════════════════════
#  HALAMAN PUBLIK
# ═══════════════════════════════════════════════════════════════════════════════
def index(request):
    return render(request, 'index.html')

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH — LOGIN / LOGOUT / REGISTER
# ═══════════════════════════════════════════════════════════════════════════════
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_admin' if request.user.is_staff else 'dashboard_user')

    # Cek pesan rate limit dari middleware
    rate_limit_msg = request.session.pop('rate_limit_msg', None)
    if rate_limit_msg:
        messages.error(request, rate_limit_msg)

    # Cek pesan session timeout
    if request.GET.get('timeout'):
        messages.warning(request, 'Sesi Anda telah berakhir karena tidak aktif. Silakan login kembali.')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user:
            log_activity(request, 'login_sukses', f'Login berhasil', user=user)
            login(request, user)
            return redirect('dashboard_admin' if (user.is_staff or user.is_superuser) else 'dashboard_user')

        log_activity(request, 'login_gagal', f'Password salah untuk username: {username}', username=username)
        messages.error(request, 'Username atau password salah.')

    return render(request, 'login.html')

def logout_view(request):
    log_activity(request, 'logout', 'User logout', user=request.user if request.user.is_authenticated else None)
    logout(request)
    return redirect('index')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard_user')

    # Cek pesan rate limit
    rate_limit_msg = request.session.pop('rate_limit_msg', None)
    if rate_limit_msg:
        messages.error(request, rate_limit_msg)

    if request.method == 'POST':
        username      = request.POST.get('username', '').strip()
        email         = request.POST.get('email', '').strip()
        password1     = request.POST.get('password1', '')
        password2     = request.POST.get('password2', '')
        full_name     = request.POST.get('full_name', '').strip()
        captcha_answer = request.POST.get('captcha_answer', '').strip()

        # Validasi CAPTCHA
        cap_valid, cap_err = validate_captcha(request.session, captcha_answer)
        if not cap_valid:
            log_activity(request, 'captcha_gagal', f'Register CAPTCHA gagal: {cap_err}', username=username)
            captcha = generate_captcha()
            set_captcha_session(request.session, captcha['answer'])
            messages.error(request, cap_err)
            return render(request, 'register.html', {'captcha': captcha})

        if not username or not password1:
            messages.error(request, 'Username dan password wajib diisi.')
        elif password1 != password2:
            messages.error(request, 'Password dan konfirmasi tidak cocok.')
        elif len(password1) < 6:
            messages.error(request, 'Password minimal 6 karakter.')
        elif User.objects.filter(username=username).exists():
            log_activity(request, 'register_gagal', f'Username sudah digunakan: {username}', username=username)
            messages.error(request, 'Username sudah digunakan.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            if full_name:
                parts = full_name.split(' ', 1)
                user.first_name = parts[0]
                user.last_name  = parts[1] if len(parts) > 1 else ''
                user.save()
            log_activity(request, 'login_sukses', f'Register dan login berhasil', user=user)
            login(request, user)
            messages.success(request, f'Selamat datang, {username}! Akun berhasil dibuat.')
            return redirect('dashboard_user')

        # Regenerate CAPTCHA setelah error lain
        captcha = generate_captcha()
        set_captcha_session(request.session, captcha['answer'])
        return render(request, 'register.html', {'captcha': captcha})

    # Generate CAPTCHA baru untuk GET request
    captcha = generate_captcha()
    set_captcha_session(request.session, captcha['answer'])
    return render(request, 'register.html', {'captcha': captcha})

# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD PAGES
# ═══════════════════════════════════════════════════════════════════════════════
@login_required(login_url='/login/')
def dashboard_user(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard_admin')
    profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
    return render(request, 'dashboard_user.html', {'user': request.user, 'profil': profil})

@login_required(login_url='/login/')
def dashboard_admin(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Akses ditolak.')
        return redirect('dashboard_user')
    return render(request, 'dashboard_admin.html', {'user': request.user})

# ═══════════════════════════════════════════════════════════════════════════════
#  PREDICT (CORE)
# ═══════════════════════════════════════════════════════════════════════════════
@login_required(login_url='/login/')
def predict(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data  = json.loads(request.body)
        mat=int(data['nilai_matematika']); bhs=int(data['nilai_bahasa'])
        ipa=int(data['nilai_ipa']);         ips=int(data['nilai_ips'])
        tek=int(data['minat_teknologi']);   sen=int(data['minat_seni'])
        bis=int(data['minat_bisnis']);      kes=int(data['minat_kesehatan'])

        # ── Cek cache prediksi ──────────────────────────────────────────
        cached = get_cached_prediction(mat, bhs, ipa, ips, tek, sen, bis, kes)
        if cached:
            # Buat record baru di DB tapi kembalikan hasil cache
            jurusan_info = get_jurusan_info()
            hr = HasilRekomendasi.objects.create(
                user=request.user, jurusan=cached['rekomendasi'], top3_data=cached.get('top3', []),
                nilai_mat=mat, nilai_bhs=bhs, nilai_ipa=ipa, nilai_ips=ips,
                minat_tek=tek, minat_sen=sen, minat_bis=bis, minat_kes=kes,
            )
            proses_gamifikasi_setelah_tes(request.user)
            result_data = dict(cached)
            result_data['id'] = hr.id
            result_data['from_cache'] = True
            return JsonResponse(result_data)

        # ── Load model dan prediksi ─────────────────────────────────────
        # pyrefly: ignore [missing-import]
        import joblib
        model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model', 'model.pkl')
        model_data = joblib.load(model_path)
        features = np.array([[mat,bhs,ipa,ips,tek,sen,bis,kes]])

        if isinstance(model_data, dict):
            dt_model = model_data.get('decision_tree') or model_data.get('model')
        else:
            dt_model = model_data

        result = dt_model.predict(features)[0]

        # Calculate Confidence Score (Decision Tree probabilities)
        try:
            proba = dt_model.predict_proba(features)[0]
            classes = dt_model.classes_
            predicted_idx = list(classes).index(result) if result in classes else 0
            confidence_score = float(proba[predicted_idx] * 100)
        except Exception:
            confidence_score = 90.0

        # Calculate Explainable AI (XAI) factors
        try:
            feature_names = [
                'nilai_matematika', 'nilai_bahasa', 'nilai_ipa', 'nilai_ips',
                'minat_teknologi', 'minat_seni', 'minat_bisnis', 'minat_kesehatan'
            ]
            feature_labels = {
                'nilai_matematika': 'Matematika', 'nilai_bahasa': 'Bahasa',
                'nilai_ipa': 'IPA', 'nilai_ips': 'IPS',
                'minat_teknologi': 'Minat Teknologi', 'minat_seni': 'Minat Seni',
                'minat_bisnis': 'Minat Bisnis', 'minat_kesehatan': 'Minat Kesehatan'
            }
            importances = dt_model.feature_importances_ if dt_model else [0.125] * 8
            user_vals = [mat, bhs, ipa, ips, tek, sen, bis, kes]
            contributions = []
            for idx, (fname, val) in enumerate(zip(feature_names, user_vals)):
                norm_val = max(0.0, min(1.0, (val - 50) / 50.0)) if 'nilai' in fname else max(0.0, min(1.0, (val - 1) / 4.0))
                contrib = float(importances[idx] * norm_val)
                contributions.append({'feature': fname, 'label': feature_labels[fname], 'value': val, 'raw_contrib': contrib})
            total_contrib = sum(c['raw_contrib'] for c in contributions) or 1.0
            for c in contributions:
                c['weight'] = round((c['raw_contrib'] / total_contrib) * 100, 1)
            contributions = sorted(contributions, key=lambda x: x['weight'], reverse=True)
        except Exception:
            contributions = [{'feature': 'nilai_matematika', 'label': 'Matematika', 'value': mat, 'weight': 100.0}]

        scores = {
            'Teknik Informatika': (mat*0.35+tek*15+(100-kes*10)*0.1),
            'Kedokteran':         (ipa*0.35+kes*15+(100-tek*10)*0.1),
            'Manajemen':          (mat*0.2+bis*15+ips*0.2),
            'Sastra':             (bhs*0.35+sen*15+(100-mat*0.3)*0.1),
            'Akuntansi':          (mat*0.25+bis*12+ips*0.25),
            'Biologi':            (ipa*0.4+kes*10+(100-tek*8)*0.1),
            'Pendidikan':         (bhs*0.25+sen*10+ips*0.2),
        }
        
        # Penyelarasan: Pastikan hasil prediksi ML (result) selalu menjadi rekomendasi teratas di Top 3
        if result in scores:
            highest_score = max(scores.values())
            if scores[result] < highest_score:
                scores[result] = highest_score + 5.0
                
        total  = sum(scores.values())
        persen = {k: round(v/total*100,1) for k,v in scores.items()}
        top3   = sorted(persen.items(), key=lambda x:x[1], reverse=True)[:3]
        jurusan_info = get_jurusan_info()
        top3_data = [{'jurusan':j,'persen':p,'info':jurusan_info.get(j,{})} for j,p in top3]

        hr = HasilRekomendasi.objects.create(
            user=request.user, jurusan=result, top3_data=top3_data,
            nilai_mat=mat,nilai_bhs=bhs,nilai_ipa=ipa,nilai_ips=ips,
            minat_tek=tek,minat_sen=sen,minat_bis=bis,minat_kes=kes,
        )
        proses_gamifikasi_setelah_tes(request.user)

        response_data = {
            'id': hr.id,
            'rekomendasi': result,
            'info': jurusan_info.get(result, {}),
            'top3': top3_data,
            'confidence_score': confidence_score,
            'explanation_factors': contributions,
            'all_scores': persen,
            'from_cache': False,
        }

        # Simpan ke cache (tanpa 'id' karena tiap user beda)
        cache_data = dict(response_data)
        cache_data.pop('id', None)
        set_cached_prediction(mat, bhs, ipa, ips, tek, sen, bis, kes, cache_data)

        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
#  USER API — PROFIL & GAMIFIKASI
# ═══════════════════════════════════════════════════════════════════════════════
@user_api_required
def api_user_profile(request):
    profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
    badges_diraih = list(UserBadge.objects.filter(user=request.user).values_list('badge', flat=True))
    total_tes = HasilRekomendasi.objects.filter(user=request.user).count()

    avatar_url = None
    if profil.avatar:
        avatar_url = request.build_absolute_uri(profil.avatar.url)

    badges_full = []
    for b in ALL_BADGES:
        badges_full.append({**b, 'diraih': b['key'] in badges_diraih})

    riwayat_poin = list(RiwayatPoin.objects.filter(user=request.user)[:5].values('jumlah','alasan','created_at'))
    for r in riwayat_poin:
        r['created_at'] = r['created_at'].strftime('%d/%m/%Y %H:%M')

    return JsonResponse({
        'username':    request.user.username,
        'full_name':   request.user.get_full_name(),
        'email':       request.user.email,
        'sekolah':     profil.sekolah,
        'kelas':       profil.kelas,
        'kota':        profil.kota,
        'bio':         profil.bio,
        'avatar_url':  avatar_url,
        'poin':        profil.poin,
        'kelengkapan': profil.kelengkapan_persen(),
        'total_tes':   total_tes,
        'badges':      badges_full,
        'badges_diraih': badges_diraih,
        'riwayat_poin': riwayat_poin,
        'date_joined': request.user.date_joined.strftime('%d %B %Y'),
    })

@user_api_required
@require_POST
def api_user_profile_update(request):
    profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
    data = json.loads(request.body)
    action = data.get('action', 'profile')

    if action == 'profile':
        full_name = data.get('full_name', '').strip()
        if full_name:
            parts = full_name.split(' ', 1)
            request.user.first_name = parts[0]
            request.user.last_name  = parts[1] if len(parts) > 1 else ''
        request.user.email = data.get('email', request.user.email)
        request.user.save()
        profil.sekolah = data.get('sekolah', profil.sekolah)
        profil.kelas   = data.get('kelas', profil.kelas)
        profil.kota    = data.get('kota', profil.kota)
        profil.bio     = data.get('bio', profil.bio)
        profil.save()

        # Cek badge profil lengkap
        if profil.kelengkapan_persen() == 100:
            cek_dan_beri_badge(request.user, 'profil_lengkap')

        return JsonResponse({'success': True, 'kelengkapan': profil.kelengkapan_persen()})

    elif action == 'password':
        old_pw = data.get('old_password', '')
        new_pw = data.get('new_password', '')
        if not request.user.check_password(old_pw):
            return JsonResponse({'error': 'Password lama salah'}, status=400)
        if len(new_pw) < 6:
            return JsonResponse({'error': 'Password baru minimal 6 karakter'}, status=400)
        request.user.set_password(new_pw)
        request.user.save()
        update_session_auth_hash(request, request.user)
        return JsonResponse({'success': True, 'message': 'Password berhasil diubah'})

    return JsonResponse({'error': 'Action tidak dikenal'}, status=400)

@user_api_required
@require_POST
def api_user_avatar(request):
    if 'avatar' not in request.FILES:
        return JsonResponse({'error': 'File tidak ditemukan'}, status=400)
    f = request.FILES['avatar']
    if not f.content_type.startswith('image/'):
        return JsonResponse({'error': 'Hanya file gambar yang diterima'}, status=400)
    if f.size > 5 * 1024 * 1024:
        return JsonResponse({'error': 'Ukuran file maksimal 5MB'}, status=400)
    profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
    if profil.avatar:
        try: os.remove(profil.avatar.path)
        except Exception: pass
    profil.avatar = f
    profil.save()
    return JsonResponse({'success': True, 'avatar_url': request.build_absolute_uri(profil.avatar.url)})


# ═══════════════════════════════════════════════════════════════════════════════
#  USER API — TES & RIWAYAT
# ═══════════════════════════════════════════════════════════════════════════════
@user_api_required
def api_user_riwayat(request):
    qs = HasilRekomendasi.objects.filter(user=request.user).order_by('-created_at')
    
    # Load model to compute confidence & XAI dynamically
    # pyrefly: ignore [missing-import]
    import joblib
    model_data = None
    try:
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'model.pkl')
        if os.path.exists(model_path):
            model_data = joblib.load(model_path)
    except Exception:
        pass

    data = []
    jurusan_info = get_jurusan_info()
    for h in qs:
        conf = 85.0
        xai = []
        if model_data:
            try:
                if isinstance(model_data, dict):
                    dt_model = model_data.get('decision_tree') or model_data.get('model')
                else:
                    dt_model = model_data

                features = np.array([[h.nilai_mat, h.nilai_bhs, h.nilai_ipa, h.nilai_ips, h.minat_tek, h.minat_sen, h.minat_bis, h.minat_kes]])
                proba = dt_model.predict_proba(features)[0]
                classes = dt_model.classes_
                pred_jurusan = h.jurusan
                predicted_idx = list(classes).index(pred_jurusan) if pred_jurusan in classes else 0
                conf = float(proba[predicted_idx] * 100)

                feature_names = [
                    'nilai_matematika', 'nilai_bahasa', 'nilai_ipa', 'nilai_ips',
                    'minat_teknologi', 'minat_seni', 'minat_bisnis', 'minat_kesehatan'
                ]
                feature_labels = {
                    'nilai_matematika': 'Matematika',
                    'nilai_bahasa': 'Bahasa',
                    'nilai_ipa': 'IPA',
                    'nilai_ips': 'IPS',
                    'minat_teknologi': 'Minat Teknologi',
                    'minat_seni': 'Minat Seni',
                    'minat_bisnis': 'Minat Bisnis',
                    'minat_kesehatan': 'Minat Kesehatan'
                }
                importances = dt_model.feature_importances_ if dt_model else [0.125] * 8
                user_vals = [h.nilai_mat, h.nilai_bhs, h.nilai_ipa, h.nilai_ips, h.minat_tek, h.minat_sen, h.minat_bis, h.minat_kes]
                contributions = []
                for idx, (fname, val) in enumerate(zip(feature_names, user_vals)):
                    if 'nilai' in fname:
                        norm_val = max(0.0, min(1.0, (val - 50) / 50.0))
                    else:
                        norm_val = max(0.0, min(1.0, (val - 1) / 4.0))
                    contrib = float(importances[idx] * norm_val)
                    contributions.append({
                        'feature': fname,
                        'label': feature_labels[fname],
                        'value': val,
                        'raw_contrib': contrib
                    })
                total_contrib = sum(c['raw_contrib'] for c in contributions)
                if total_contrib == 0: total_contrib = 1.0
                for c in contributions:
                    c['weight'] = round((c['raw_contrib'] / total_contrib) * 100, 1)
                xai = sorted(contributions, key=lambda x: x['weight'], reverse=True)
            except Exception:
                pass

        hist_scores = {
            'Teknik Informatika': (h.nilai_mat*0.35+h.minat_tek*15+(100-h.minat_kes*10)*0.1),
            'Kedokteran':         (h.nilai_ipa*0.35+h.minat_kes*15+(100-h.minat_tek*10)*0.1),
            'Manajemen':          (h.nilai_mat*0.2+h.minat_bis*15+h.nilai_ips*0.2),
            'Sastra':             (h.nilai_bhs*0.35+h.minat_sen*15+(100-h.nilai_mat*0.3)*0.1),
            'Akuntansi':          (h.nilai_mat*0.25+h.minat_bis*12+h.nilai_ips*0.25),
            'Biologi':            (h.nilai_ipa*0.4+h.minat_kes*10+(100-h.minat_tek*8)*0.1),
            'Pendidikan':         (h.nilai_bhs*0.25+h.minat_sen*10+h.nilai_ips*0.2),
        }
        hist_total  = sum(hist_scores.values())
        hist_persen = {k: round(v/hist_total*100,1) for k,v in hist_scores.items()}

        data.append({
            'id':        h.id,
            'jurusan':   h.jurusan,
            'icon':      jurusan_info.get(h.jurusan, {}).get('icon', '🎓'),
            'top3':      h.top3_data,
            'nilai_mat': h.nilai_mat, 'nilai_bhs': h.nilai_bhs,
            'nilai_ipa': h.nilai_ipa, 'nilai_ips': h.nilai_ips,
            'minat_tek': h.minat_tek, 'minat_sen': h.minat_sen,
            'minat_bis': h.minat_bis, 'minat_kes': h.minat_kes,
            'tanggal':   h.created_at.strftime('%d %b %Y, %H:%M'),
            'tanggal_short': h.created_at.strftime('%d/%m'),
            'confidence_score': conf,
            'explanation_factors': xai,
            'all_scores': hist_persen,
        })
    return JsonResponse({'riwayat': data, 'total': len(data)})

@user_api_required
def api_user_riwayat_delete(request, hasil_id):
    h = get_object_or_404(HasilRekomendasi, pk=hasil_id)
    if request.method == 'DELETE':
        if not request.user.is_staff and h.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        h.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@user_api_required
def api_user_export_pdf(request, hasil_id):
    """Render halaman cetak yang bisa di-print/save sebagai PDF."""
    h = get_object_or_404(HasilRekomendasi, pk=hasil_id, user=request.user)
    jurusan_info = get_jurusan_info()
    info = jurusan_info.get(h.jurusan, {})
    context = {
        'hasil': h,
        'info':  info,
        'user':  request.user,
    }
    return render(request, 'print_hasil.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
#  USER API — INFORMATIF
# ═══════════════════════════════════════════════════════════════════════════════
@user_api_required
def api_jurusan_list_user(request):
    """Daftar semua jurusan dengan info dasar."""
    jurusan_info = get_jurusan_info()
    result = []
    for nama, info in jurusan_info.items():
        detail = JurusanDetail.objects.filter(nama=nama).first()
        result.append({
            'nama': nama,
            'icon': info['icon'],
            'deskripsi': info['deskripsi'],
            'prospek': info['prospek'],
            'has_detail': detail is not None,
            'gelar': detail.gelar if detail else '',
            'lama_studi': detail.lama_studi if detail else '4 Tahun',
        })
    return JsonResponse({'jurusan': result})


@user_api_required
def api_jurusan_detail_user(request, nama):
    """Detail lengkap satu jurusan."""
    jurusan_info = get_jurusan_info()
    info = jurusan_info.get(nama, {})
    detail = JurusanDetail.objects.filter(nama=nama).first()

    # Badge explorer
    cek_dan_beri_badge(request.user, 'explorer')

    return JsonResponse({
        'nama': nama,
        'icon': info.get('icon', '🎓'),
        'deskripsi': info.get('deskripsi', ''),
        'prospek': info.get('prospek', []),
        'mata_kuliah': detail.mata_kuliah if detail else [],
        'universitas': detail.universitas if detail else [],
        'biaya_min': detail.biaya_min if detail else 0,
        'biaya_max': detail.biaya_max if detail else 0,
        'passing_grade': detail.passing_grade if detail else 0,
        'lama_studi': detail.lama_studi if detail else '4 Tahun',
        'gelar': detail.gelar if detail else '',
        'deskripsi_panjang': detail.deskripsi_panjang if detail else info.get('deskripsi',''),
    })

@user_api_required
@require_POST
def api_kalkulator_ptn(request):
    """Hitung estimasi peluang masuk PTN berdasarkan rata-rata nilai UTBK."""
    data = json.loads(request.body)
    tes_potensi = float(data.get('tes_potensi', 500))
    tes_literasi = float(data.get('tes_literasi', 500))
    tes_matematika = float(data.get('tes_matematika', 500))
    rata = (tes_potensi + tes_literasi + tes_matematika) / 3

    # Passing grade per prodi (data representatif)
    prodi_data = [
        {'prodi':'Teknik Informatika','univ':'UI','pg':720,'ket':'Sangat Kompetitif'},
        {'prodi':'Teknik Informatika','univ':'ITB','pg':750,'ket':'Sangat Kompetitif'},
        {'prodi':'Teknik Informatika','univ':'UGM','pg':710,'ket':'Sangat Kompetitif'},
        {'prodi':'Teknik Informatika','univ':'ITS','pg':680,'ket':'Kompetitif'},
        {'prodi':'Kedokteran','univ':'UI','pg':800,'ket':'Sangat Kompetitif'},
        {'prodi':'Kedokteran','univ':'UGM','pg':790,'ket':'Sangat Kompetitif'},
        {'prodi':'Kedokteran','univ':'UNAIR','pg':770,'ket':'Sangat Kompetitif'},
        {'prodi':'Manajemen','univ':'UI','pg':700,'ket':'Kompetitif'},
        {'prodi':'Manajemen','univ':'UGM','pg':690,'ket':'Kompetitif'},
        {'prodi':'Akuntansi','univ':'UI','pg':710,'ket':'Kompetitif'},
        {'prodi':'Akuntansi','univ':'UNDIP','pg':660,'ket':'Sedang'},
        {'prodi':'Sastra Indonesia','univ':'UI','pg':620,'ket':'Sedang'},
        {'prodi':'Pendidikan Biologi','univ':'UNY','pg':580,'ket':'Cukup'},
        {'prodi':'Pendidikan','univ':'UNY','pg':570,'ket':'Cukup'},
        {'prodi':'Biologi','univ':'IPB','pg':630,'ket':'Sedang'},
    ]
    results = []
    for p in prodi_data:
        diff = rata - p['pg']
        if diff >= 50:   peluang, warna = 'Tinggi', 'green'
        elif diff >= 0:  peluang, warna = 'Sedang', 'orange'
        elif diff >= -50: peluang, warna = 'Kecil', 'red'
        else:             peluang, warna = 'Sangat Kecil', 'red'
        results.append({**p, 'peluang': peluang, 'warna': warna, 'selisih': round(diff)})

    results.sort(key=lambda x: x['pg'], reverse=True)
    return JsonResponse({'rata': round(rata,1), 'results': results})

@user_api_required
def api_user_artikel(request):
    """Daftar artikel yang dipublikasikan."""
    cek_dan_beri_badge(request.user, 'pembaca')
    data = list(Artikel.objects.filter(is_published=True).values(
        'id','judul','kategori','konten','created_at'))
    for d in data:
        d['created_at'] = d['created_at'].strftime('%d %b %Y')
        d['ringkasan']  = d['konten'][:120] + '...' if len(d['konten']) > 120 else d['konten']
    return JsonResponse({'artikel': data})

def api_user_faq(request):
    data = list(FAQ.objects.filter(is_active=True).values('id','pertanyaan','jawaban','urutan'))
    return JsonResponse({'faq': data})

@user_api_required
def api_user_badges(request):
    badges_diraih = list(UserBadge.objects.filter(user=request.user).values('badge','diraih_at'))
    diraih_keys   = {b['badge'] for b in badges_diraih}
    for b in badges_diraih:
        b['diraih_at'] = b['diraih_at'].strftime('%d/%m/%Y')
    all_b = []
    for b in ALL_BADGES:
        all_b.append({**b, 'diraih': b['key'] in diraih_keys})
    return JsonResponse({'badges': all_b, 'diraih_count': len(diraih_keys)})


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN API ENDPOINTS (tidak berubah, salin dari sebelumnya)
# ═══════════════════════════════════════════════════════════════════════════════
@admin_required
def api_dashboard_stats(request):
    now = timezone.now(); today = now.date()
    month_start = today.replace(day=1)
    total_users   = User.objects.filter(is_staff=False, is_superuser=False).count()
    tes_hari_ini  = HasilRekomendasi.objects.filter(created_at__date=today).count()
    tes_bulan_ini = HasilRekomendasi.objects.filter(created_at__date__gte=month_start).count()
    total_tes     = HasilRekomendasi.objects.count()
    distribusi = HasilRekomendasi.objects.values('jurusan').annotate(total=Count('id')).order_by('-total')
    pie_data   = [{'jurusan':d['jurusan'],'total':d['total']} for d in distribusi]
    line_data  = []
    for i in range(6,-1,-1):
        day = today - timedelta(days=i)
        count = HasilRekomendasi.objects.filter(created_at__date=day).count()
        line_data.append({'tanggal':day.strftime('%d/%m'),'total':count})
    user_growth = []
    for i in range(6,-1,-1):
        day = today - timedelta(days=i)
        count = User.objects.filter(date_joined__date__lte=day).count()
        user_growth.append({'tanggal':day.strftime('%d/%m'),'total':count})
    return JsonResponse({'total_users':total_users,'tes_hari_ini':tes_hari_ini,
        'tes_bulan_ini':tes_bulan_ini,'total_tes':total_tes,
        'pie_data':pie_data,'line_data':line_data,'user_growth':user_growth})

@admin_required
def api_users_list(request):
    q=request.GET.get('q','').strip(); status=request.GET.get('status','all')
    qs=User.objects.all().order_by('-date_joined')
    if status=='active':   qs=User.objects.filter(is_active=True).order_by('-date_joined')
    elif status=='suspended': qs=User.objects.filter(is_active=False).order_by('-date_joined')
    if q: qs=qs.filter(username__icontains=q)|qs.filter(email__icontains=q)
    users=[]
    for u in qs:
        tes_count=HasilRekomendasi.objects.filter(user=u).count()
        last_tes=HasilRekomendasi.objects.filter(user=u).first()
        users.append({'id':u.id,'username':u.username,'email':u.email,'full_name':u.get_full_name() or '-',
            'is_active':u.is_active,'is_staff':u.is_staff,'is_superuser':u.is_superuser,
            'date_joined':u.date_joined.strftime('%d/%m/%Y'),'tes_count':tes_count,
            'last_tes':last_tes.created_at.strftime('%d/%m/%Y') if last_tes else '-'})
    return JsonResponse({'users':users,'total':len(users)})

@admin_required
@require_POST
def api_user_toggle(request, user_id):
    target=get_object_or_404(User,pk=user_id)
    if target==request.user:
        return JsonResponse({'error':'Tidak bisa menonaktifkan akun sendiri'},status=400)
    target.is_active=not target.is_active; target.save()
    return JsonResponse({'success':True,'is_active':target.is_active,'status':'diaktifkan' if target.is_active else 'dinonaktifkan'})

@admin_required
def api_admin_user_detail(request, user_id):
    """Detail lengkap user (ProfilSiswa + HasilRekomendasi)."""
    target = get_object_or_404(User, pk=user_id)
    profil, _ = ProfilSiswa.objects.get_or_create(user=target)
    
    # Riwayat tes
    riwayat_qs = HasilRekomendasi.objects.filter(user=target).order_by('-created_at')
    riwayat = []
    for h in riwayat_qs:
        riwayat.append({
            'id': h.id,
            'jurusan': h.jurusan,
            'nilai_mat': h.nilai_mat,
            'nilai_bhs': h.nilai_bhs,
            'nilai_ipa': h.nilai_ipa,
            'nilai_ips': h.nilai_ips,
            'minat_tek': h.minat_tek,
            'minat_sen': h.minat_sen,
            'minat_bis': h.minat_bis,
            'minat_kes': h.minat_kes,
            'tanggal': h.created_at.strftime('%d/%m/%Y %H:%M'),
        })
        
    return JsonResponse({
        'id': target.id,
        'username': target.username,
        'email': target.email,
        'full_name': target.get_full_name() or '-',
        'is_active': target.is_active,
        'date_joined': target.date_joined.strftime('%d/%m/%Y %H:%M'),
        'sekolah': profil.sekolah or '-',
        'kelas': profil.kelas or '-',
        'kota': profil.kota or '-',
        'bio': profil.bio or '-',
        'avatar_url': profil.avatar.url if profil.avatar else None,
        'riwayat': riwayat,
        'tes_count': len(riwayat),
    })

@admin_required
def api_export_users(request):
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="users_jurusanku.csv"'
    response.write('\ufeff')
    writer=csv.writer(response)
    writer.writerow(['No','Username','Email','Nama Lengkap','Status','Role','Tgl Daftar','Jumlah Tes'])
    for i,u in enumerate(User.objects.all().order_by('-date_joined'),1):
        tes_count=HasilRekomendasi.objects.filter(user=u).count()
        writer.writerow([i,u.username,u.email,u.get_full_name() or '-',
            'Aktif' if u.is_active else 'Nonaktif',
            'Superuser' if u.is_superuser else ('Admin' if u.is_staff else 'Siswa'),
            u.date_joined.strftime('%d/%m/%Y'),tes_count])
    return response

@admin_required
def api_jurusan_list(request):
    if request.method=='GET':
        data=list(JurusanInfo.objects.values('id','nama','icon','deskripsi','prospek','is_active','updated_at'))
        for d in data: d['updated_at']=d['updated_at'].strftime('%d/%m/%Y') if d['updated_at'] else '-'
        return JsonResponse({'jurusan':data})
    if request.method=='POST':
        body=json.loads(request.body)
        j=JurusanInfo.objects.create(nama=body['nama'],icon=body.get('icon','🎓'),
            deskripsi=body['deskripsi'],prospek=body.get('prospek',[]))
        return JsonResponse({'success':True,'id':j.id})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_jurusan_detail(request, jurusan_id):
    j=get_object_or_404(JurusanInfo,pk=jurusan_id)
    if request.method=='PUT':
        body=json.loads(request.body)
        j.nama=body.get('nama',j.nama); j.icon=body.get('icon',j.icon)
        j.deskripsi=body.get('deskripsi',j.deskripsi); j.prospek=body.get('prospek',j.prospek)
        j.is_active=body.get('is_active',j.is_active); j.save()
        return JsonResponse({'success':True})
    if request.method=='DELETE':
        j.delete(); return JsonResponse({'success':True})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_artikel_list(request):
    if request.method=='GET':
        data=list(Artikel.objects.values('id','judul','kategori','konten','is_published','created_at'))
        for d in data: d['created_at']=d['created_at'].strftime('%d/%m/%Y')
        return JsonResponse({'artikel':data})
    if request.method=='POST':
        body=json.loads(request.body)
        a=Artikel.objects.create(judul=body['judul'],konten=body['konten'],
            kategori=body.get('kategori','Tips'),is_published=body.get('is_published',True))
        return JsonResponse({'success':True,'id':a.id})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_artikel_detail(request, artikel_id):
    a=get_object_or_404(Artikel,pk=artikel_id)
    if request.method=='GET':
        return JsonResponse({'id':a.id,'judul':a.judul,'konten':a.konten,'kategori':a.kategori,'is_published':a.is_published})
    if request.method=='PUT':
        body=json.loads(request.body)
        a.judul=body.get('judul',a.judul); a.konten=body.get('konten',a.konten)
        a.kategori=body.get('kategori',a.kategori); a.is_published=body.get('is_published',a.is_published)
        a.save(); return JsonResponse({'success':True})
    if request.method=='DELETE':
        a.delete(); return JsonResponse({'success':True})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_faq_list(request):
    if request.method=='GET':
        data=list(FAQ.objects.values('id','pertanyaan','jawaban','urutan','is_active'))
        return JsonResponse({'faq':data})
    if request.method=='POST':
        body=json.loads(request.body)
        f=FAQ.objects.create(pertanyaan=body['pertanyaan'],jawaban=body['jawaban'],urutan=body.get('urutan',0))
        return JsonResponse({'success':True,'id':f.id})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_faq_detail(request, faq_id):
    f=get_object_or_404(FAQ,pk=faq_id)
    if request.method=='PUT':
        body=json.loads(request.body)
        f.pertanyaan=body.get('pertanyaan',f.pertanyaan); f.jawaban=body.get('jawaban',f.jawaban)
        f.urutan=body.get('urutan',f.urutan); f.is_active=body.get('is_active',f.is_active)
        f.save(); return JsonResponse({'success':True})
    if request.method=='DELETE':
        f.delete(); return JsonResponse({'success':True})
    return JsonResponse({'error':'Method not allowed'},status=405)

@admin_required
def api_analytics(request):
    distribusi=HasilRekomendasi.objects.values('jurusan').annotate(total=Count('id')).order_by('-total')
    avg=HasilRekomendasi.objects.aggregate(mat=Avg('nilai_mat'),bhs=Avg('nilai_bhs'),
        ipa=Avg('nilai_ipa'),ips=Avg('nilai_ips'),tek=Avg('minat_tek'),
        sen=Avg('minat_sen'),bis=Avg('minat_bis'),kes=Avg('minat_kes'))
    rata_nilai={k:round(v or 0,1) for k,v in avg.items()}
    heatmap=defaultdict(int)
    for h in HasilRekomendasi.objects.values_list('created_at',flat=True):
        local=timezone.localtime(h) if timezone.is_aware(h) else h
        heatmap[f"{local.weekday()}_{local.hour}"]+=1
    heatmap_data=[{'day':int(k.split('_')[0]),'hour':int(k.split('_')[1]),'value':v} for k,v in heatmap.items()]
    return JsonResponse({'distribusi':list(distribusi),'rata_nilai':rata_nilai,'heatmap':heatmap_data})

@admin_required
def api_export_laporan(request):
    now=timezone.now(); bulan=request.GET.get('bulan',now.strftime('%Y-%m'))
    try: year,month=map(int,bulan.split('-'))
    except ValueError: year,month=now.year,now.month
    qs=HasilRekomendasi.objects.filter(created_at__year=year,created_at__month=month).select_related('user').order_by('-created_at')
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']=f'attachment; filename="laporan_{bulan}.csv"'
    response.write('\ufeff')
    writer=csv.writer(response)
    writer.writerow(['No','Tanggal','Username','Jurusan Rekomendasi','Mat','Bhs','IPA','IPS','Tek','Sen','Bis','Kes'])
    for i,h in enumerate(qs,1):
        writer.writerow([i,h.created_at.strftime('%d/%m/%Y %H:%M'),
            h.user.username if h.user else 'anonim',h.jurusan,
            h.nilai_mat,h.nilai_bhs,h.nilai_ipa,h.nilai_ips,
            h.minat_tek,h.minat_sen,h.minat_bis,h.minat_kes])
    return response

@admin_required
def api_ml_status(request):
    active=ModelVersion.objects.filter(status='active').first()
    history=list(ModelVersion.objects.values('id','versi','akurasi','algoritma','dataset_size','status','catatan','created_at')[:10])
    for h in history:
        h['created_at']=h['created_at'].strftime('%d/%m/%Y %H:%M')
        h['akurasi_pct']=f"{h['akurasi']*100:.1f}%" if h['akurasi'] else '-'
        
    accuracies_data = {
        'decision_tree': 0.91,
    }
    try:
        # pyrefly: ignore [missing-import]
        import joblib
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'model.pkl')
        if os.path.exists(model_path):
            model_data = joblib.load(model_path)
            if isinstance(model_data, dict) and 'accuracies' in model_data:
                accuracies_data = model_data['accuracies']
    except Exception as e:
        print("Error loading comparative accuracies:", e)

    return JsonResponse({
        'active':{
            'versi':active.versi if active else '1.0',
            'akurasi':active.akurasi if active else 0.91,
            'akurasi_pct':f"{(active.akurasi or 0.91)*100:.1f}%",
            'algoritma':active.algoritma if active else 'Decision Tree',
            'dataset_size':active.dataset_size if active else 1000,
            'status':active.status if active else 'active',
        },
        'history':history,
        'accuracies': accuracies_data
    })

@admin_required
@require_POST
def api_ml_retrain(request):
    try:
        ModelVersion.objects.filter(status='active').update(status='archived')
        train_script=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'ml_model','train_best.py')
        result=subprocess.run([sys.executable,train_script],capture_output=True,text=True,timeout=120)
        
        algoritma = 'Decision Tree'
        akurasi = 0.90
        for line in result.stdout.splitlines():
            if 'Model terbaik terpilih:' in line:
                try:
                    parts = line.split('Model terbaik terpilih:')[1].strip()
                    algo_part, acc_part = parts.split('(Akurasi:')
                    algoritma = algo_part.strip()
                    akurasi = float(acc_part.replace('%', '').replace(')', '').strip()) / 100.0
                except Exception:
                    pass

        latest=ModelVersion.objects.order_by('-created_at').first()
        try: ver_num=float(latest.versi)+0.1 if latest else 1.0
        except Exception: ver_num=1.1
        ver_str=f"{ver_num:.1f}"
        
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'dataset.csv')
        dataset_size = 1000
        if os.path.exists(dataset_path):
            with open(dataset_path, 'r') as f:
                dataset_size = sum(1 for line in f) - 1
                
        ModelVersion.objects.create(versi=ver_str,akurasi=akurasi,algoritma=algoritma,
            dataset_size=dataset_size,status='active',catatan='Retrain via dashboard admin',created_by=request.user)
        return JsonResponse({'success':True,'versi':ver_str,'akurasi':akurasi,'akurasi_pct':f"{akurasi*100:.1f}%",'output':result.stdout[-500:]})
    except subprocess.TimeoutExpired:
        return JsonResponse({'error':'Retrain timeout (>120s)'},status=500)
    except Exception as e:
        return JsonResponse({'error':str(e)},status=500)

@admin_required
@require_POST
def api_ml_upload(request):
    if 'dataset' not in request.FILES:
        return JsonResponse({'error':'File tidak ditemukan'},status=400)
    f=request.FILES['dataset']
    if not f.name.endswith('.csv'):
        return JsonResponse({'error':'Hanya file CSV yang diterima'},status=400)
    try:
        import io
        content=f.read().decode('utf-8')
        reader=csv.DictReader(io.StringIO(content))
        rows=list(reader)
        return JsonResponse({'success':True,'filename':f.name,'rows':len(rows),'columns':reader.fieldnames,'preview':rows[:3]})
    except Exception as e:
        return JsonResponse({'error':str(e)},status=500)


# ─── API: TESTIMONI ──────────────────────────────────────────────────────────
def api_testimoni(request):
    if request.method == 'GET':
        testis = Testimoni.objects.filter(is_active=True)[:6]
        data = []
        for t in testis:
            avatar_url = None
            if hasattr(t.user, 'profil') and t.user.profil.avatar:
                avatar_url = request.build_absolute_uri(t.user.profil.avatar.url)
            
            data.append({
                'id': t.id,
                'username': t.user.username,
                'full_name': t.user.get_full_name() or t.user.username,
                'bintang': t.bintang,
                'ulasan': t.ulasan,
                'sekolah': t.user.profil.sekolah if hasattr(t.user, 'profil') else '',
                'avatar_url': avatar_url,
                'created_at': t.created_at.strftime('%d/%m/%Y')
            })
        return JsonResponse({'testimoni': data})
    
    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body)
            bintang = int(body.get('bintang', 5))
            ulasan = body.get('ulasan', '').strip()
            if not ulasan:
                return JsonResponse({'error': 'Ulasan tidak boleh kosong'}, status=400)
            
            t, created = Testimoni.objects.update_or_create(
                user=request.user,
                defaults={'bintang': bintang, 'ulasan': ulasan, 'is_active': True}
            )
            return JsonResponse({'success': True, 'msg': 'Testimoni berhasil disimpan!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# ─── API: FORUM DISKUSI ──────────────────────────────────────────────────────
@login_required(login_url='/login/')
def api_forum_list(request):
    if request.method == 'GET':
        kat = request.GET.get('kategori', 'all')
        posts = ForumPost.objects.all()
        if kat != 'all':
            posts = posts.filter(kategori=kat)
        
        data = []
        for p in posts:
            data.append({
                'id': p.id,
                'username': p.user.username,
                'full_name': p.user.get_full_name() or p.user.username,
                'role': 'Admin' if (p.user.is_staff or p.user.is_superuser) else 'Siswa',
                'judul': p.judul,
                'konten': p.konten,
                'kategori': p.kategori,
                'comment_count': p.comments.count(),
                'created_at': p.created_at.strftime('%d %b %Y %H:%M')
            })
        return JsonResponse({'posts': data})
    
    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            judul = body.get('judul', '').strip()
            konten = body.get('konten', '').strip()
            kategori = body.get('kategori', 'Umum').strip()
            
            if not judul or not konten:
                return JsonResponse({'error': 'Judul dan konten wajib diisi'}, status=400)
            
            p = ForumPost.objects.create(
                user=request.user,
                judul=judul,
                konten=konten,
                kategori=kategori
            )
            if hasattr(request.user, 'profil'):
                request.user.profil.tambah_poin(10, 'Membuat diskusi baru di forum')
                
            return JsonResponse({'success': True, 'id': p.id, 'msg': 'Topik berhasil dibuat! (+10 ⭐)'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='/login/')
def api_forum_detail(request, post_id):
    try:
        p = ForumPost.objects.get(id=post_id)
        comments = []
        for c in p.comments.all():
            comments.append({
                'id': c.id,
                'username': c.user.username,
                'full_name': c.user.get_full_name() or c.user.username,
                'role': 'Admin' if (c.user.is_staff or c.user.is_superuser) else 'Siswa',
                'konten': c.konten,
                'created_at': c.created_at.strftime('%d %b %Y %H:%M')
            })
        
        return JsonResponse({
            'post': {
                'id': p.id,
                'username': p.user.username,
                'full_name': p.user.get_full_name() or p.user.username,
                'role': 'Admin' if (p.user.is_staff or p.user.is_superuser) else 'Siswa',
                'judul': p.judul,
                'konten': p.konten,
                'kategori': p.kategori,
                'created_at': p.created_at.strftime('%d %b %Y %H:%M')
            },
            'comments': comments
        })
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Topik tidak ditemukan'}, status=404)


@login_required(login_url='/login/')
@require_POST
def api_forum_comment(request, post_id):
    try:
        p = ForumPost.objects.get(id=post_id)
        body = json.loads(request.body)
        konten = body.get('konten', '').strip()
        if not konten:
            return JsonResponse({'error': 'Komentar tidak boleh kosong'}, status=400)
        
        c = ForumComment.objects.create(
            post=p,
            user=request.user,
            konten=konten
        )
        if hasattr(request.user, 'profil'):
            request.user.profil.tambah_poin(5, 'Membalas diskusi di forum')
            
        return JsonResponse({'success': True, 'id': c.id, 'msg': 'Komentar berhasil ditambahkan! (+5 ⭐)'})
    except ForumPost.DoesNotExist:
        return JsonResponse({'error': 'Topik tidak ditemukan'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─── API: SISWA SERUPA MEMILIH ───────────────────────────────────────────────
@login_required(login_url='/login/')
def api_similar_users(request):
    try:
        hr_curr = HasilRekomendasi.objects.filter(user=request.user).order_by('-created_at').first()
        other_results = HasilRekomendasi.objects.exclude(user=request.user).select_related('user', 'user__profil')
        
        similar_list = []
        
        if hr_curr:
            curr_vector = np.array([
                hr_curr.nilai_mat, hr_curr.nilai_bhs, hr_curr.nilai_ipa, hr_curr.nilai_ips,
                hr_curr.minat_tek, hr_curr.minat_sen, hr_curr.minat_bis, hr_curr.minat_kes
            ])
            
            users_latest = {}
            for hr in other_results:
                if hr.user and hr.user.id not in users_latest:
                    users_latest[hr.user.id] = hr
            
            for uid, hr in users_latest.items():
                other_vector = np.array([
                    hr.nilai_mat, hr.nilai_bhs, hr.nilai_ipa, hr.nilai_ips,
                    hr.minat_tek, hr.minat_sen, hr.minat_bis, hr.minat_kes
                ])
                dist = np.linalg.norm(curr_vector - other_vector)
                match_score = round(max(0.0, 100.0 - (dist / 1.5)), 1)
                
                raw_uname = hr.user.username
                masked_uname = raw_uname[0] + '***' + raw_uname[-1] if len(raw_uname) > 2 else raw_uname[0] + '***'
                
                similar_list.append({
                    'username': masked_uname,
                    'sekolah': hr.user.profil.sekolah if hasattr(hr.user, 'profil') else 'SMA',
                    'kelas': hr.user.profil.kelas if hasattr(hr.user, 'profil') else '',
                    'jurusan': hr.jurusan,
                    'match_score': match_score,
                })
            
            similar_list = sorted(similar_list, key=lambda x: x['match_score'], reverse=True)[:3]
            
        else:
            users_latest = {}
            for hr in other_results:
                if hr.user and hr.user.id not in users_latest:
                    users_latest[hr.user.id] = hr
            
            for uid, hr in list(users_latest.items())[:3]:
                raw_uname = hr.user.username
                masked_uname = raw_uname[0] + '***' + raw_uname[-1] if len(raw_uname) > 2 else raw_uname[0] + '***'
                
                similar_list.append({
                    'username': masked_uname,
                    'sekolah': hr.user.profil.sekolah if hasattr(hr.user, 'profil') else 'SMA',
                    'kelas': hr.user.profil.kelas if hasattr(hr.user, 'profil') else '',
                    'jurusan': hr.jurusan,
                    'match_score': 85.0,
                })
                
        return JsonResponse({
            'has_rekomendasi': bool(hr_curr),
            'similar_users': similar_list
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─── API: REAL-TIME LEARNING FEEDBACK ─────────────────────────────────────────
import threading

def run_background_retrain(user):
    def run():
        try:
            train_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'train_best.py')
            # Run the training script python
            result = subprocess.run([sys.executable, train_script], capture_output=True, text=True, timeout=120)
            
            algoritma = 'Decision Tree'
            akurasi = 0.90
            for line in result.stdout.splitlines():
                if 'Model terbaik terpilih:' in line:
                    try:
                        parts = line.split('Model terbaik terpilih:')[1].strip()
                        algo_part, acc_part = parts.split('(Akurasi:')
                        algoritma = algo_part.strip()
                        akurasi = float(acc_part.replace('%', '').replace(')', '').strip()) / 100.0
                    except Exception:
                        pass

            # Read dataset size
            dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'dataset.csv')
            dataset_size = 1000
            if os.path.exists(dataset_path):
                with open(dataset_path, 'r') as f:
                    dataset_size = sum(1 for line in f) - 1

            latest = ModelVersion.objects.order_by('-created_at').first()
            try:
                ver_num = float(latest.versi) + 0.1 if latest else 1.0
            except Exception:
                ver_num = 1.1
            ver_str = f"{ver_num:.1f}"

            ModelVersion.objects.filter(status='active').update(status='archived')
            ModelVersion.objects.create(
                versi=ver_str,
                akurasi=akurasi,
                algoritma=algoritma,
                dataset_size=dataset_size,
                status='active',
                catatan='Retrain otomatis via feedback user',
                created_by=user
            )
            print(f"Background retrain completed successfully: v{ver_str}, accuracy {akurasi}")
        except Exception as e:
            print(f"Background retrain failed: {e}")

    threading.Thread(target=run).start()


@login_required(login_url='/login/')
@require_POST
def api_user_feedback(request):
    try:
        data = json.loads(request.body)
        rekomendasi_id = data.get('rekomendasi_id')
        is_correct = data.get('is_correct')
        corrected_major = data.get('corrected_major')

        hr = get_object_or_404(HasilRekomendasi, id=rekomendasi_id, user=request.user)

        final_major = hr.jurusan if is_correct else corrected_major
        if not final_major:
            return JsonResponse({'error': 'Jurusan koreksi tidak boleh kosong jika tidak sesuai'}, status=400)

        # Menambahkan data umpan balik ke dataset.csv
        dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_model', 'dataset.csv')

        with open(dataset_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                hr.nilai_mat, hr.nilai_bhs, hr.nilai_ipa, hr.nilai_ips,
                hr.minat_tek, hr.minat_sen, hr.minat_bis, hr.minat_kes,
                final_major
            ])

        # Pemicu training ulang model secara otomatis di background
        run_background_retrain(request.user)

        # Invalidate cache prediksi setelah retrain
        invalidate_prediction_cache()

        # Reward user +5 poin
        profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
        profil.tambah_poin(5, 'Memberikan umpan balik model AI')

        return JsonResponse({
            'success': True,
            'message': 'Terima kasih atas umpan balik Anda! Model AI sedang dilatih ulang di latar belakang. (+5 ⭐)'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
#  WHATSAPP SHARE
# ═══════════════════════════════════════════════════════════════════════════════
@user_api_required
def api_share_whatsapp(request, hasil_id):
    """Generate WhatsApp deep link untuk berbagi hasil rekomendasi."""
    try:
        hr = get_object_or_404(HasilRekomendasi, pk=hasil_id, user=request.user)
        jurusan_info = get_jurusan_info()
        info = jurusan_info.get(hr.jurusan, {})
        icon = info.get('icon', '🎓')

        top3_text = ''
        if hr.top3_data:
            for i, item in enumerate(hr.top3_data[:3], 1):
                top3_text += f"\n  {i}. {item['jurusan']} ({item['persen']}%)"

        months = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
            7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        tgl_indo = f"{hr.created_at.day} {months.get(hr.created_at.month)} {hr.created_at.year}"

        text = (
            f"🎓 *Hasil Analisis Rekomendasi Jurusan — JurusanKu ID*\n\n"
            f"Halo! Saya baru saja menyelesaikan asesmen minat dan bakat di platform JurusanKu ID. Berikut adalah rekomendasi program studi yang paling sesuai untuk saya:\n\n"
            f"✨ *Rekomendasi Utama:* {icon} *{hr.jurusan}*\n"
            f"📊 *Alternatif Pilihan Program Studi:*{top3_text}\n\n"
            f"📅 Asesmen diselesaikan pada: {tgl_indo}\n\n"
            f"Temukan rekomendasi jurusan kuliah terbaik Anda dengan teknologi AI di: http://{request.get_host()}"
        )

        wa_url = f"https://wa.me/?text={urllib.parse.quote(text)}"
        return JsonResponse({'success': True, 'wa_url': wa_url, 'text': text})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN API: ACTIVITY LOG
# ═══════════════════════════════════════════════════════════════════════════════
@admin_required
def api_activity_log(request):
    """Ambil log aktivitas keamanan untuk admin panel."""
    jenis_filter = request.GET.get('jenis', 'all')
    q = request.GET.get('q', '').strip()
    page_size = 50

    qs = AktivitasLog.objects.select_related('user').order_by('-created_at')
    if jenis_filter != 'all':
        qs = qs.filter(jenis=jenis_filter)
    if q:
        qs = qs.filter(username__icontains=q) | AktivitasLog.objects.filter(keterangan__icontains=q)

    data = []
    for log in qs[:page_size]:
        data.append({
            'id': log.id,
            'username': log.username or (log.user.username if log.user else '—'),
            'jenis': log.jenis,
            'jenis_label': log.get_jenis_display(),
            'ip_address': log.ip_address or '—',
            'keterangan': log.keterangan,
            'created_at': log.created_at.strftime('%d/%m/%Y %H:%M:%S'),
        })

    # Statistik ringkas
    # pyrefly: ignore [missing-import]
    from django.utils import timezone as tz
    today = tz.now().date()
    stats = {
        'login_gagal_hari_ini': AktivitasLog.objects.filter(jenis='login_gagal', created_at__date=today).count(),
        'rate_limit_hari_ini': AktivitasLog.objects.filter(jenis='rate_limit', created_at__date=today).count(),
        'total_log': AktivitasLog.objects.count(),
    }

    return JsonResponse({'logs': data, 'total': len(data), 'stats': stats})


@admin_required
def api_activity_log_clear(request):
    """Hapus log lama (lebih dari 30 hari) untuk menjaga performa DB."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    # pyrefly: ignore [missing-import]
    from django.utils import timezone as tz
    cutoff = tz.now() - timedelta(days=30)
    deleted, _ = AktivitasLog.objects.filter(created_at__lt=cutoff).delete()
    return JsonResponse({'success': True, 'deleted': deleted})


@require_POST
def api_kontak_submit(request):
    """Menerima input dari form Hubungi Kami (kontak) dan menyimpannya di DB."""
    try:
        data = json.loads(request.body)
        nama = data.get('nama', '').strip()
        sekolah = data.get('sekolah', '').strip()
        telepon = data.get('telepon', '').strip()
        email = data.get('email', '').strip()
        subjek = data.get('subjek', '').strip()
        pesan = data.get('pesan', '').strip()

        if not (nama and sekolah and telepon and email and subjek and pesan):
            return JsonResponse({'error': 'Semua field wajib diisi.'}, status=400)

        # Simpan ke DB
        PesanKontak.objects.create(
            nama=nama, sekolah=sekolah, telepon=telepon,
            email=email, subjek=subjek, pesan=pesan
        )
        return JsonResponse({'success': True, 'message': 'Pesan Anda berhasil dikirim!'})
    except Exception as e:
        return JsonResponse({'error': f'Terjadi kesalahan: {str(e)}'}, status=500)


@admin_required
def api_admin_pesan_list(request):
    """Mengembalikan daftar pesan kontak untuk admin."""
    pesan_qs = PesanKontak.objects.all()
    
    # Filter pencarian
    q = request.GET.get('q', '').strip()
    if q:
        pesan_qs = pesan_qs.filter(
            Q(nama__icontains=q) |
            Q(sekolah__icontains=q) |
            Q(email__icontains=q) |
            Q(subjek__icontains=q) |
            Q(pesan__icontains=q)
        )

    data = []
    for p in pesan_qs:
        data.append({
            'id': p.id,
            'nama': p.nama,
            'sekolah': p.sekolah,
            'telepon': p.telepon,
            'email': p.email,
            'subjek': p.subjek,
            'pesan': p.pesan,
            'created_at': p.created_at.strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse({'pesan': data, 'total': len(data)})


@admin_required
def api_admin_pesan_delete(request, pesan_id):
    """Menghapus pesan kontak tertentu."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    pesan = get_object_or_404(PesanKontak, id=pesan_id)
    pesan.delete()
    return JsonResponse({'success': True})


# ═══════════════════════════════════════════════════════════════════════════════
#  AI CAREER MENTOR VIEWS
# ═══════════════════════════════════════════════════════════════════════════════
@user_api_required
def api_chat_sessions(request):
    """GET: List all chat sessions for the logged-in user.
    POST: Create a new chat session."""
    if request.method == 'GET':
        sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
        data = []
        for s in sessions:
            data.append({
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.strftime('%d/%m/%Y %H:%M'),
                'updated_at': s.updated_at.strftime('%d/%m/%Y %H:%M'),
            })
        return JsonResponse({'sessions': data})
        
    elif request.method == 'POST':
        try:
            # Judul default adalah Konseling Karir Baru
            title = 'Konseling Karir Baru'
            
            # Jika ada payload judul kustom
            if request.body:
                try:
                    payload = json.loads(request.body)
                    if payload.get('title'):
                        title = payload.get('title').strip()[:150]
                except Exception:
                    pass

            session = ChatSession.objects.create(user=request.user, title=title)
            
            # Tambahkan greeting awal otomatis dari AI ke DB
            greeting = f"Halo {request.user.get_full_name() or request.user.username}! Saya adalah AI Career Mentor Anda. Ada yang bisa saya bantu diskusikan tentang minat atau hasil rekomendasi jurusan Anda hari ini?"
            ChatMessage.objects.create(session=session, sender='ai', content=greeting)

            return JsonResponse({
                'success': True,
                'session': {
                    'id': session.id,
                    'title': session.title,
                    'created_at': session.created_at.strftime('%d/%m/%Y %H:%M'),
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@user_api_required
def api_chat_history(request, session_id):
    """GET: Retrieve chat messages for a specific session."""
    session = get_object_or_404(ChatSession, pk=session_id)
    if not request.user.is_staff and session.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    messages_qs = session.messages.all().order_by('created_at')
    data = []
    for msg in messages_qs:
        data.append({
            'id': msg.id,
            'sender': msg.sender,
            'content': msg.content,
            'created_at': msg.created_at.strftime('%H:%M'),
        })
    return JsonResponse({'messages': data, 'session_title': session.title})


@user_api_required
@require_POST
def api_chat_send(request, session_id):
    """POST: Send a new message, call Gemini API, save and return AI response."""
    session = get_object_or_404(ChatSession, pk=session_id)
    if not request.user.is_staff and session.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    try:
        data = json.loads(request.body)
        user_message_text = data.get('message', '').strip()
        if not user_message_text:
            return JsonResponse({'error': 'Pesan tidak boleh kosong.'}, status=400)
            
        # 1. Simpan pesan user ke DB
        user_msg = ChatMessage.objects.create(session=session, sender='user', content=user_message_text)
        
        # Auto-rename judul sesi jika masih bernilai default 'Konseling Karir Baru'
        if session.title == 'Konseling Karir Baru':
            clean_text = user_message_text.strip()
            clean_text = " ".join(clean_text.split())
            if len(clean_text) > 30:
                session.title = clean_text[:27] + "..."
            else:
                session.title = clean_text
            session.save(update_fields=['title', 'updated_at'])
        else:
            session.save(update_fields=['updated_at'])
        
        # Inisialisasi API Key dari settings
        api_key = django_settings.GEMINI_API_KEY
        if not api_key:
            # Fallback ke mock response yang mendidik jika API key belum diset
            mock_content = (
                "Halo! Koneksi ke AI Career Mentor berhasil disimulasikan. Namun, saat ini administrator belum mengatur kunci API `GEMINI_API_KEY` di server. "
                "Untuk mengaktifkan konseling AI yang sesungguhnya secara gratis, silakan masukkan variabel lingkungan `GEMINI_API_KEY` dari Google AI Studio ke dalam pengaturan sistem Anda.\n\n"
                "Sebagai simulasi bimbingan: Saya melihat Anda sangat tertarik untuk merencanakan karir masa depan Anda. Silakan hubungi admin Anda untuk melanjutkan percakapan cerdas ini!"
            )
            ai_msg = ChatMessage.objects.create(session=session, sender='ai', content=mock_content)
            
            # Beri poin gamifikasi
            profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
            profil.tambah_poin(2, 'Berinteraksi dengan AI Mentor')
            
            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': user_msg.id,
                    'content': user_msg.content,
                    'created_at': user_msg.created_at.strftime('%H:%M')
                },
                'ai_message': {
                    'id': ai_msg.id,
                    'content': ai_msg.content,
                    'created_at': ai_msg.created_at.strftime('%H:%M')
                },
                'session_title': session.title,
                'user_poin': profil.poin
            })
            
        # 2. Ambil konteks siswa (profil & hasil rekomendasi terbaru)
        profil, _ = ProfilSiswa.objects.get_or_create(user=request.user)
        latest_rec = HasilRekomendasi.objects.filter(user=request.user).first()
        
        # Buat context profil
        profile_context = (
            f"Nama: {request.user.get_full_name() or request.user.username}\n"
            f"Sekolah: {profil.sekolah or 'Belum diisi'}\n"
            f"Kelas: {profil.kelas or 'Belum diisi'}\n"
            f"Kota: {profil.kota or 'Belum diisi'}\n"
            f"Bio: {profil.bio or 'Belum diisi'}\n"
        )
        
        # Buat context rekomendasi
        rec_context = ""
        if latest_rec:
            rec_context = (
                f"Hasil rekomendasi teratas: {latest_rec.jurusan}\n"
                f"Nilai Akademik: Matematika ({latest_rec.nilai_mat}), Bahasa ({latest_rec.nilai_bhs}), IPA ({latest_rec.nilai_ipa}), IPS ({latest_rec.nilai_ips})\n"
                f"Minat: Teknologi ({latest_rec.minat_tek}), Seni ({latest_rec.minat_sen}), Bisnis ({latest_rec.minat_bis}), Kesehatan ({latest_rec.minat_kes})\n"
                f"Pilihan Top 3 Jurusan Lainnya: {', '.join([item['jurusan'] + ' (' + str(item['persen']) + '%)' for item in latest_rec.top3_data])}\n"
            )
        else:
            rec_context = "Siswa belum pernah melakukan tes rekomendasi jurusan kuliah.\n"
            
        system_instruction = (
            "Kamu adalah AI Career Mentor (Konselor Karir Virtual) yang ramah, profesional, dan empatik untuk siswa sekolah menengah (SMA/SMK) di Indonesia. "
            "Tugas utamanya adalah membantu siswa merencanakan masa depan akademik, memahami hasil tes jurusan mereka, "
            "mengeksplorasi karir, dan memberikan bimbingan belajar/tips UTBK.\n\n"
            "Gunakan informasi profil dan hasil tes rekomendasi berikut untuk mempersonalisasi setiap jawabanmu:\n"
            "--- PROFIL SISWA ---\n"
            f"{profile_context}\n"
            "--- HASIL REKOMENDASI TERAKHIR ---\n"
            f"{rec_context}\n"
            "--- KETENTUAN JAWABAN ---\n"
            "1. Panggil siswa dengan namanya agar lebih akrab.\n"
            "2. Gunakan bahasa Indonesia yang santun, kasual, suportif, dan memotivasi khas anak muda.\n"
            "3. Jika siswa belum melakukan tes, sarankan mereka untuk melakukan tes rekomendasi terlebih dahulu di platform JurusanKu ID.\n"
            "4. Berikan jawaban terstruktur dengan bullet points jika membahas opsi karir atau universitas agar mudah dibaca.\n"
            "5. Meskipun fokus utamamu adalah bimbingan karir dan pendidikan, kamu tetap diperbolehkan menjawab pertanyaan umum lainnya di luar konteks tersebut dengan ramah jika ditanyakan oleh siswa."
        )
        
        # 3. Load model Gemini dan kirim pesan
        # pyrefly: ignore [missing-import]
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Load history dari database (maksimal 15 pesan terakhir)
        db_messages = session.messages.all().order_by('created_at')
        
        # Format history untuk API Gemini (menggunakan schema role: user/model)
        # Catatan: Kita tidak menyertakan pesan user terakhir yang baru saja kita simpan, 
        # karena akan dikirim lewat send_message(). Jadi ambil N-1 pesan sebelumnya.
        history = []
        for msg in db_messages[:db_messages.count()-1]:
            history.append({
                'role': 'user' if msg.sender == 'user' else 'model',
                'parts': [msg.content]
            })
            
        # Konfigurasi Google Search Grounding secara langsung menggunakan Protobuf
        google_search_tool = genai.protos.Tool(
            google_search=genai.protos.Tool.GoogleSearch()
        )
        
        model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            system_instruction=system_instruction,
            tools=[google_search_tool]
        )
        
        chat = model.start_chat(history=history)
        response = chat.send_message(user_message_text)
        ai_response_text = response.text
        
        # 4. Simpan respon AI ke DB
        ai_msg = ChatMessage.objects.create(session=session, sender='ai', content=ai_response_text)
        
        # 5. Poin gamifikasi: Cek apakah hari ini sudah melebihi limit poin untuk chat
        today_chat_count = RiwayatPoin.objects.filter(
            user=request.user, 
            alasan='Berinteraksi dengan AI Mentor',
            created_at__date=timezone.now().date()
        ).count()
        
        user_poin = profil.poin
        if today_chat_count < 3:
            profil.tambah_poin(2, 'Berinteraksi dengan AI Mentor')
            user_poin = profil.poin
            # Cek badge poin_100
            if profil.poin >= 100:
                cek_dan_beri_badge(request.user, 'poin_100')
                
        return JsonResponse({
            'success': True,
            'user_message': {
                'id': user_msg.id,
                'content': user_msg.content,
                'created_at': user_msg.created_at.strftime('%H:%M')
            },
            'ai_message': {
                'id': ai_msg.id,
                'content': ai_msg.content,
                'created_at': ai_msg.created_at.strftime('%H:%M')
            },
            'session_title': session.title,
            'user_poin': user_poin
        })
        
    except Exception as e:
        try:
            from google.api_core.exceptions import ResourceExhausted
            if isinstance(e, ResourceExhausted):
                return JsonResponse({
                    'error': 'Batas kuota atau rate limit (429) API Gemini terlampaui. Silakan tunggu beberapa saat sebelum mencoba kembali.'
                }, status=429)
        except ImportError:
            pass
        return JsonResponse({'error': str(e)}, status=500)


@user_api_required
def api_chat_session_delete(request, session_id):
    """DELETE: Safely delete a chat session."""
    session = get_object_or_404(ChatSession, pk=session_id)
    if not request.user.is_staff and session.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
        
    if request.method == 'DELETE':
        session.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

