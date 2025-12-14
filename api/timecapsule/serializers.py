from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    year = serializers.SerializerMethodField()
    tags = serializers.StringRelatedField(many=True)

    class Meta:
        model = Post
        fields = ['id', 'url', 'local_file', 'media_type', 'thumb_url', 'description', 'year', 'tags']

    def get_year(self, obj):
        # REVISI: Menggunakan 'posttime_set' (default nama dari Django)
        # .first() mengambil data pertama yang ketemu.
        # Jika tidak ada data, dia akan return None (aman, tidak error).
        if hasattr(obj, 'posttime_set'):
            time_data = obj.posttime_set.first()
            if time_data:
                return time_data.year
        
        # Jaga-jaga jika pakai OneToOneField (tanpa _set)
        elif hasattr(obj, 'posttime'):
            return obj.posttime.year

        return None