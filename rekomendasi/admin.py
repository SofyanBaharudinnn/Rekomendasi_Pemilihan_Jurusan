# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import (
    ProfilSiswa, UserBadge, RiwayatPoin, JurusanDetail,
    HasilRekomendasi, JurusanInfo, Artikel, FAQ, ModelVersion,
    Testimoni, ForumPost, ForumComment, AktivitasLog, PesanKontak
)

admin.site.register(ProfilSiswa)
admin.site.register(UserBadge)
admin.site.register(RiwayatPoin)
admin.site.register(JurusanDetail)
admin.site.register(HasilRekomendasi)
admin.site.register(JurusanInfo)
admin.site.register(Artikel)
admin.site.register(FAQ)
admin.site.register(ModelVersion)
admin.site.register(Testimoni)
admin.site.register(ForumPost)
admin.site.register(ForumComment)
admin.site.register(PesanKontak)


@admin.register(AktivitasLog)
class AktivitasLogAdmin(admin.ModelAdmin):
    list_display  = ('jenis', 'username', 'ip_address', 'keterangan_singkat', 'created_at')
    list_filter   = ('jenis', 'created_at')
    search_fields = ('username', 'ip_address', 'keterangan')
    readonly_fields = ('user', 'username', 'jenis', 'ip_address', 'user_agent', 'keterangan', 'created_at')
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'

    def keterangan_singkat(self, obj):
        return obj.keterangan[:60] + '...' if len(obj.keterangan) > 60 else obj.keterangan
    keterangan_singkat.short_description = 'Keterangan'

    def has_add_permission(self, request):
        return False  # Log tidak bisa dibuat manual dari admin

