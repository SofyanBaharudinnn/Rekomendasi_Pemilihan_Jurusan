from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rekomendasi.models import ProfilSiswa, HasilRekomendasi
import json

class AdminUserDetailAPITests(TestCase):
    def setUp(self):
        # Create users
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.id',
            password='adminpassword'
        )
        self.siswa = User.objects.create_user(
            username='siswa',
            email='siswa@test.id',
            password='siswapassword',
            first_name='Siswa',
            last_name='Budi'
        )
        
        # Populate ProfilSiswa for siswa (created automatically by signal, but let's update fields)
        self.profil_siswa = ProfilSiswa.objects.get(user=self.siswa)
        self.profil_siswa.sekolah = 'SMA Negeri 1'
        self.profil_siswa.kelas = 'XII IPA 1'
        self.profil_siswa.kota = 'Merauke'
        self.profil_siswa.bio = 'Ingin jadi programer handal'
        self.profil_siswa.save()
        
        # Populate HasilRekomendasi for siswa
        self.hasil1 = HasilRekomendasi.objects.create(
            user=self.siswa,
            jurusan='Teknik Informatika',
            nilai_mat=90,
            nilai_bhs=80,
            nilai_ipa=85,
            nilai_ips=70,
            minat_tek=95,
            minat_sen=50,
            minat_bis=60,
            minat_kes=40
        )
        self.hasil2 = HasilRekomendasi.objects.create(
            user=self.siswa,
            jurusan='Sistem Informasi',
            nilai_mat=85,
            nilai_bhs=85,
            nilai_ipa=80,
            nilai_ips=75,
            minat_tek=90,
            minat_sen=55,
            minat_bis=70,
            minat_kes=45
        )
        
        # Update created_at deterministically (SQLite in test runs might have identical timestamps otherwise)
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        HasilRekomendasi.objects.filter(id=self.hasil1.id).update(created_at=now - timedelta(hours=1))
        HasilRekomendasi.objects.filter(id=self.hasil2.id).update(created_at=now)


    def test_anonymous_user_denied(self):
        url = reverse('api_admin_user_detail', kwargs={'user_id': self.siswa.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Login required')

    def test_non_admin_user_denied(self):
        self.client.login(username='siswa', password='siswapassword')
        url = reverse('api_admin_user_detail', kwargs={'user_id': self.siswa.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Admin only')

    def test_admin_user_success(self):
        self.client.login(username='admin', password='adminpassword')
        url = reverse('api_admin_user_detail', kwargs={'user_id': self.siswa.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['id'], self.siswa.id)
        self.assertEqual(data['username'], 'siswa')
        self.assertEqual(data['email'], 'siswa@test.id')
        self.assertEqual(data['full_name'], 'Siswa Budi')
        self.assertEqual(data['sekolah'], 'SMA Negeri 1')
        self.assertEqual(data['kelas'], 'XII IPA 1')
        self.assertEqual(data['kota'], 'Merauke')
        self.assertEqual(data['bio'], 'Ingin jadi programer handal')
        self.assertEqual(data['tes_count'], 2)
        
        # Check riwayat results
        self.assertEqual(len(data['riwayat']), 2)
        # Order should be descending by created_at (h2 then h1)
        self.assertEqual(data['riwayat'][0]['jurusan'], 'Sistem Informasi')
        self.assertEqual(data['riwayat'][0]['nilai_mat'], 85)
        self.assertEqual(data['riwayat'][1]['jurusan'], 'Teknik Informatika')
        self.assertEqual(data['riwayat'][1]['nilai_mat'], 90)

