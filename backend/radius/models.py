from django.db import models


class RadiusCheck(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default=":=")
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = "radcheck"
        verbose_name = "RADIUS check attribute"
        verbose_name_plural = "RADIUS check attributes"

    def __str__(self):
        return f"{self.username}: {self.attribute}"


class RadiusReply(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default="=")
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = "radreply"
        verbose_name = "RADIUS reply attribute"
        verbose_name_plural = "RADIUS reply attributes"

    def __str__(self):
        return f"{self.username}: {self.attribute}"