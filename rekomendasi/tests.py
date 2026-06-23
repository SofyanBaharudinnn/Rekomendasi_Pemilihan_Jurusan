# pyrefly: ignore [missing-import]
from django.test import TestCase
# pyrefly: ignore [missing-import]
from django.contrib.auth.models import User
# pyrefly: ignore [missing-import]
from django.urls import reverse
from rekomendasi.models import ProfilSiswa, HasilRekomendasi, PesanKontak, ChatSession, ChatMessage
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
        # pyrefly: ignore [missing-import]
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


class PesanKontakAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.id',
            password='adminpassword'
        )
        self.siswa = User.objects.create_user(
            username='siswa',
            email='siswa@test.id',
            password='siswapassword'
        )
        
    def test_submit_contact_message(self):
        url = reverse('api_kontak_submit')
        payload = {
            'nama': 'Pengirim Test',
            'sekolah': 'SMA Test',
            'telepon': '08123456789',
            'email': 'pengirim@test.id',
            'subjek': 'Tanya Rekomendasi',
            'pesan': 'Halo, ini adalah pesan test dari unit test.'
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify saved in database
        self.assertEqual(PesanKontak.objects.count(), 1)
        pesan = PesanKontak.objects.first()
        self.assertEqual(pesan.nama, 'Pengirim Test')
        self.assertEqual(pesan.subjek, 'Tanya Rekomendasi')
        
    def test_submit_contact_message_missing_fields(self):
        url = reverse('api_kontak_submit')
        payload = {
            'nama': 'Pengirim Test',
            'email': 'pengirim@test.id'
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        
    def test_admin_list_messages_anonymous_denied(self):
        url = reverse('api_admin_pesan_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        
    def test_admin_list_messages_non_admin_denied(self):
        self.client.login(username='siswa', password='siswapassword')
        url = reverse('api_admin_pesan_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        
    def test_admin_list_and_delete_messages_success(self):
        # Create a test message
        p = PesanKontak.objects.create(
            nama='Budi',
            sekolah='SMA 1',
            telepon='0811111111',
            email='budi@test.id',
            subjek='Tanya Jurusan',
            pesan='Apa jurusan yang cocok?'
        )
        
        # Login as admin
        self.client.login(username='admin', password='adminpassword')
        
        # Get list
        url_list = reverse('api_admin_pesan_list')
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['pesan'][0]['nama'], 'Budi')
        
        # Search filter test
        response_search = self.client.get(f"{url_list}?q=Budi")
        self.assertEqual(response_search.status_code, 200)
        data_search = json.loads(response_search.content)
        self.assertEqual(data_search['total'], 1)

        response_search_empty = self.client.get(f"{url_list}?q=NotPresent")
        self.assertEqual(response_search_empty.status_code, 200)
        data_search_empty = json.loads(response_search_empty.content)
        self.assertEqual(data_search_empty['total'], 0)
        
        # Delete message
        url_delete = reverse('api_admin_pesan_delete', kwargs={'pesan_id': p.id})
        response_delete = self.client.post(url_delete)
        self.assertEqual(response_delete.status_code, 200)
        
        # Verify deleted
        self.assertEqual(PesanKontak.objects.count(), 0)


class RiwayatDeleteAPITests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.id',
            password='adminpassword'
        )
        self.siswa = User.objects.create_user(
            username='siswa',
            email='siswa@test.id',
            password='siswapassword'
        )
        self.siswa2 = User.objects.create_user(
            username='siswa2',
            email='siswa2@test.id',
            password='siswa2password'
        )
        
        self.hasil_siswa = HasilRekomendasi.objects.create(
            user=self.siswa,
            jurusan='Teknik Informatika',
            nilai_mat=90, nilai_bhs=80, nilai_ipa=85, nilai_ips=70,
            minat_tek=95, minat_sen=50, minat_bis=60, minat_kes=40
        )
        
    def test_anonymous_user_delete_denied(self):
        url = reverse('api_user_riwayat_delete', kwargs={'hasil_id': self.hasil_siswa.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 401)
        
    def test_user_delete_own_riwayat_success(self):
        self.client.login(username='siswa', password='siswapassword')
        url = reverse('api_user_riwayat_delete', kwargs={'hasil_id': self.hasil_siswa.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(HasilRekomendasi.objects.filter(id=self.hasil_siswa.id).exists())
        
    def test_user_delete_other_riwayat_denied(self):
        self.client.login(username='siswa2', password='siswa2password')
        url = reverse('api_user_riwayat_delete', kwargs={'hasil_id': self.hasil_siswa.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(HasilRekomendasi.objects.filter(id=self.hasil_siswa.id).exists())
        
    def test_admin_delete_any_riwayat_success(self):
        self.client.login(username='admin', password='adminpassword')
        url = reverse('api_user_riwayat_delete', kwargs={'hasil_id': self.hasil_siswa.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(HasilRekomendasi.objects.filter(id=self.hasil_siswa.id).exists())


class AICareerMentorAPITests(TestCase):
    def setUp(self):
        self.siswa = User.objects.create_user(
            username='siswa_test',
            email='siswa_test@test.id',
            password='testpassword'
        )
        self.other_user = User.objects.create_user(
            username='siswa2_test',
            email='siswa2_test@test.id',
            password='testpassword'
        )
        
    def test_anonymous_access_denied(self):
        url = reverse('api_chat_sessions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        
        response_post = self.client.post(url)
        self.assertEqual(response_post.status_code, 401)
        
    def test_create_and_list_sessions(self):
        self.client.login(username='siswa_test', password='testpassword')
        
        # POST to create session
        url = reverse('api_chat_sessions')
        response = self.client.post(url, data=json.dumps({'title': 'Diskusi Informatika'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['session']['title'], 'Diskusi Informatika')
        
        # Verify automatic greeting was created
        session_id = data['session']['id']
        session = ChatSession.objects.get(id=session_id)
        self.assertEqual(session.messages.count(), 1)
        self.assertEqual(session.messages.first().sender, 'ai')
        
        # GET to list sessions
        response_get = self.client.get(url)
        self.assertEqual(response_get.status_code, 200)
        data_get = json.loads(response_get.content)
        self.assertEqual(len(data_get['sessions']), 1)
        self.assertEqual(data_get['sessions'][0]['id'], session_id)
        self.assertEqual(data_get['sessions'][0]['title'], 'Diskusi Informatika')

    def test_chat_history_and_permission(self):
        self.client.login(username='siswa_test', password='testpassword')
        session = ChatSession.objects.create(user=self.siswa, title='Sesi Test')
        ChatMessage.objects.create(session=session, sender='user', content='Halo Mentor')
        ChatMessage.objects.create(session=session, sender='ai', content='Halo Siswa')
        
        url = reverse('api_chat_history', kwargs={'session_id': session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['messages']), 2)
        self.assertEqual(data['messages'][0]['sender'], 'user')
        self.assertEqual(data['messages'][1]['sender'], 'ai')
        
        # Login as other user to test permission denied
        self.client.logout()
        self.client.login(username='siswa2_test', password='testpassword')
        response_other = self.client.get(url)
        self.assertEqual(response_other.status_code, 403)

    def test_send_message_simulation(self):
        self.client.login(username='siswa_test', password='testpassword')
        session = ChatSession.objects.create(user=self.siswa, title='Sesi Test')
        
        url = reverse('api_chat_send', kwargs={'session_id': session.id})
        payload = {'message': 'Bagaimana prospek kerja IT?'}
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['user_message']['content'], 'Bagaimana prospek kerja IT?')
        self.assertIn('Koneksi ke AI Career Mentor berhasil', data['ai_message']['content']) # Mock warning message
        
        # Verify saved in DB
        self.assertEqual(session.messages.count(), 2)
        
    def test_delete_session(self):
        self.client.login(username='siswa_test', password='testpassword')
        session = ChatSession.objects.create(user=self.siswa, title='Sesi Hapus')
        
        url = reverse('api_chat_session_delete', kwargs={'session_id': session.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(ChatSession.objects.filter(id=session.id).exists())



