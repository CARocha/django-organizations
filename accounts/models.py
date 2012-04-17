from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from accounts.managers import AccountManager


class AccountsBase(models.Model):
    """
    Just a little helper
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Account(AccountsBase):
    """
    This is the umbrella object under which all account users fall.

    The class has multiple account users and one that is designated the account
    owner.
    """
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, blank=True, null=True,
            unique=True)
    domain = models.CharField(max_length=100, blank=True, null=True,
            unique=True)
    is_active = models.BooleanField(default=True)

    objects = AccountManager()

    class Meta:
        ordering = ['name']
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")

    def __unicode__(self):
        return u"%s" % self.name

    def save(self, *args, **kwargs):
        if self.subdomain == "":
            self.subdomain = None
        if self.domain == "":
            self.domain = None
        super(Account, self).save(*args, **kwargs)

    @permalink
    def get_absolute_url(self):
        return ('account_detail', (), {'account_pk': self.pk})

    def is_member(self, user):
        """
        Returns a boolean value designating whether the User is a member of the
        account.
        """
        return True if self.objects.users.filter(user=user) else False


class AccountUser(AccountsBase):
    """
    This relates a User object to the account group. It is possible for a User
    to be a member of multiple accounts, so this class relates the AccountUser
    to the User model using a ForeignKey relationship, rather than a OneToOne
    relationship.

    Authentication and general user information is handled by the User class
    and the contrib.auth application.
    """
    user = models.ForeignKey(User, related_name="accountusers")
    account = models.ForeignKey(Account, related_name="users")
    is_admin = models.BooleanField(default=False)

    class Meta:
        ordering = ['account', 'user']
        unique_together = ('user', 'account')
        verbose_name = _("Account user")
        verbose_name_plural = _("Account users")

    def __unicode__(self):
        return u"%s" % self.user

    def delete(self, using=None):
        """
        If the account user is also the owner, this should not be deleted
        unless it's part of a cascade from the Account.
        """
        from accounts.exceptions import OwnershipRequired
        if self.account.owner.id == self.id:
            raise OwnershipRequired("Cannot delete account owner before"
                                    "account or transferring ownership")
        else:
            super(AccountUser, self).delete(using=using)

    @permalink
    def get_absolute_url(self):
        return ('accountuser_detail', (),
                {'account_pk': self.account.pk, 'accountuser_pk': self.pk})

    @property
    def full_name(self):
        return u"%s %s" % (self.user.first_name, self.user.last_name)


class AccountOwner(AccountsBase):
    """
    Each account must have one and only one account owner.
    """
    account = models.OneToOneField(Account, related_name="owner")
    account_user = models.OneToOneField(AccountUser, related_name="owned_accounts")

    class Meta:
        verbose_name = _("Account owner")
        verbose_name_plural = _("Account owners")

    def __unicode__(self):
        return u"%s: %s" % (self.account, self.account_user)

    def save(self, *args, **kwargs):
        """
        Ensure that the account owner is actually an account user
        """
        from accounts.exceptions import AccountMismatch
        if self.account_user.account != self.account:
            raise AccountMismatch
        else:
            super(AccountOwner, self).save(*args, **kwargs)
