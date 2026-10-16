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


class RadiusReply(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=64)
    attribute = models.CharField(max_length=64)
    op = models.CharField(max_length=2, default="=")
    value = models.CharField(max_length=253)

    class Meta:
        managed = False
        db_table = "radreply"


class RadAcct(models.Model):
    radacctid = models.BigAutoField(
        primary_key=True,
    )

    acctsessionid = models.TextField()
    acctuniqueid = models.TextField()

    username = models.TextField(
        null=True,
        blank=True,
    )

    realm = models.TextField(
        null=True,
        blank=True,
    )

    nasipaddress = models.GenericIPAddressField()

    nasportid = models.TextField(
        null=True,
        blank=True,
    )

    nasporttype = models.TextField(
        null=True,
        blank=True,
    )

    acctstarttime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctupdatetime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctstoptime = models.DateTimeField(
        null=True,
        blank=True,
    )

    acctinterval = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctsessiontime = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctauthentic = models.TextField(
        null=True,
        blank=True,
    )

    connectinfo_start = models.TextField(
        null=True,
        blank=True,
    )

    connectinfo_stop = models.TextField(
        null=True,
        blank=True,
    )

    acctinputoctets = models.BigIntegerField(
        null=True,
        blank=True,
    )

    acctoutputoctets = models.BigIntegerField(
        null=True,
        blank=True,
    )

    calledstationid = models.TextField(
        null=True,
        blank=True,
    )

    callingstationid = models.TextField(
        null=True,
        blank=True,
    )

    acctterminatecause = models.TextField(
        null=True,
        blank=True,
    )

    servicetype = models.TextField(
        null=True,
        blank=True,
    )

    framedprotocol = models.TextField(
        null=True,
        blank=True,
    )

    framedipaddress = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedipv6address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedipv6prefix = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    framedinterfaceid = models.TextField(
        null=True,
        blank=True,
    )

    delegatedipv6prefix = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class_value = models.TextField(
        db_column="class",
        null=True,
        blank=True,
    )

    class Meta:
        managed = False
        db_table = "radacct"
        ordering = [
            "-acctstarttime",
        ]

    def __str__(self):
        return (
            f"{self.username or 'unknown'} "
            f"- {self.acctsessionid}"
        )

    @property
    def is_active(self):
        return (
            self.acctstarttime is not None
            and self.acctstoptime is None
        )

    @property
    def total_bytes(self):
        return (
            (self.acctinputoctets or 0)
            + (self.acctoutputoctets or 0)
        )