from django.db import models


class Language(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Language"
        db_table = "language"


class Translate(models.Model):
    key = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    lang = models.ForeignKey(Language, on_delete=models.CASCADE)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name_plural = "Translate"
        db_table = "translate"
