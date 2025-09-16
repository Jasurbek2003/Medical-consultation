from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Translate, Language
from rest_framework.permissions import AllowAny, BasePermission


class DoesntAllow(BasePermission):
    """
    Allow any access.
    This isn't strictly required, since you could use an empty
    permission_classes list, but it's useful because it makes the intention
    more explicit.
    """

    def has_permission(self, request, view):
        return False
class TranslateApiView(APIView):
    def get_permissions(self):
        """
        Allow anyone to access GET requests, require authentication for other methods
        """
        if self.request.method == 'GET' or (self.request.method == 'POST' and self.request.user.username == "akbar"):
            print(self.request.user)
            return [AllowAny()]
        # return [IsAuthenticated()]
        return [DoesntAllow()]


    @staticmethod
    def get(request, lang):
        all_keys = Translate.objects.all().values_list('key', flat=True)
        translates = Translate.objects.filter(lang__name=lang)
        data = {}
        for translate in translates:
            data[translate.key] = translate.value
        for key in all_keys:
            if key not in data:
                data[key] = key
        return Response(data)

    @staticmethod
    def post(request, lang):
        language = Language.objects.get(name=lang) if Language.objects.filter(name=lang).exists() else None
        if language is None:
            return Response({
                'error': 'Language not found'
            }, status=404)
        for i in request.data:
            key = i
            value = request.data[i]
            if Translate.objects.filter(key=key, lang=language).exists():
                translate = Translate.objects.get(key=key, lang=language)
                translate.value = value
                translate.save()
            else:
                Translate.objects.create(key=key, value=value, lang=language)
        return Response({
            'success': True
        })

    @staticmethod
    def delete(request):
        key = request.GET.get('key')
        if Translate.objects.filter(key=key).exists():
            translate = Translate.objects.filter(key=key)
            translate.delete()
            return Response({
                'success': True
            })
        else:
            return Response({
                'error': 'Translate not found'
            }, status=404)


class LanguageApiView(APIView):
    def get_permissions(self):
        """
        Allow anyone to access GET requests, require authentication for other methods
        """
        if self.request.method == 'GET' or (self.request.method == 'POST' and self.request.user.username == "akbar"):
            return [AllowAny()]
        # return [IsAuthenticated()]
        return False

    @staticmethod
    def get(request):
        languages = Language.objects.all()
        data = []
        for language in languages:
            data.append(language.name)
        return Response(data)

    @staticmethod
    def post(request):
        name = request.data.get('name')
        if Language.objects.filter(name=name).exists():
            return Response({
                'error': 'Language already exists'
            }, status=400)
        else:
            language = Language.objects.create(name=name)
            return Response({
                'name': language.name
            })

    @staticmethod
    def delete(request):
        name = request.data.get('name')
        if Language.objects.filter(name=name).exists():
            language = Language.objects.get(name=name)
            language.delete()
            return Response({
                'success': True
            })
        else:
            return Response({
                'error': 'Language not found'
            }, status=404)


class TranslateAdminApiView(APIView):
    def get_permissions(self):
        """
        Allow anyone to access GET requests, require authentication for other methods
        """
        if self.request.method == 'GET' or (self.request.method == 'POST' and self.request.user.username == "akbar"):
            return [AllowAny()]
        # return [IsAuthenticated()]
        return False
    @staticmethod
    def get(request):
        all_keys_2 = Translate.objects.all().values("key", "id")
        all_keys = []
        keys_list = []
        for i in all_keys_2:
            if i["key"] not in keys_list:
                all_keys.append(i)
                keys_list.append(i["key"])
        translates = Translate.objects.all()
        all_languages = Language.objects.all()
        data = []
        for key in all_keys:
            translate = {
                'key': key['key'],
                'id': key['id']
            }
            for language in all_languages:
                translate[language.name] = translates.filter(
                    key=key['key'], lang=language).values_list('value', flat=True)[0] if translates.filter(
                    key=key['key'], lang=language).exists() else None
            data.append(translate)

        for i in request.GET:
            if i.startswith("filter["):
                new_data = []
                filter_name = i[7:-1]
                for j in data:
                    if str(j[filter_name]) == request.GET[i]:
                        new_data.append(j)
                data = new_data

        if "search" in request.GET:
            new_data = []
            for i in data:
                for j in i.values():
                    if str(j).lower().startswith(request.GET["search"].lower()):
                        new_data.append(i)
                        break
            data = new_data

        if "sort" in request.GET:
            if request.GET["sort"].startswith("-"):
                data = sorted(data, key=lambda k: k[request.GET["sort"][1:]], reverse=True)
            else:
                data = sorted(data, key=lambda k: k[request.GET["sort"]])

        page = int(request.GET.get('page', 1))
        if page < 1:
            page = 1
        per_page = int(request.GET.get('per_page', 10))
        if per_page < 1:
            per_page = 10
        all_data = data
        data = data[(page - 1) * per_page:page * per_page]
        return Response({
            'data': data,
            "page": page,
            "per_page": per_page,
            "all_data": len(all_data),
            "pages": len(all_data) // per_page + 1,
            "this_page_url": f"?page={page}&per_page={per_page}",
            "next_page_url": f"?page={page + 1}&per_page={per_page}" if len(all_data) > page * per_page else "",
            "prev_page_url": f"?page={page - 1}&per_page={per_page}" if page > 1 else "",
            "from": (page - 1) * per_page + 1,
            "to": page * per_page if len(all_data) > page * per_page else len(all_data),
            "last_page": len(all_data) // per_page + 1,
        })
