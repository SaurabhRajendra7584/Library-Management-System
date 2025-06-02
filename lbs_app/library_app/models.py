# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Book(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
    ]

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True, help_text="13-digit ISBN")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='books')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    publication_date = models.DateField()
    publisher = models.CharField(max_length=255)
    pages = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)

    # Digital Resources
    pdf_file = models.FileField(upload_to='ebooks/', blank=True, null=True,
                                help_text="Upload PDF version of the book")

    # Inventory
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
            models.Index(fields=['isbn']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def is_available(self):
        return self.status == 'available' and self.available_copies > 0

    def can_be_borrowed(self):
        return self.is_available()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    membership_date = models.DateTimeField(auto_now_add=True)
    max_books_allowed = models.PositiveIntegerField(default=5)
    is_active_member = models.BooleanField(default=True)

    # Notifications preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} - Profile"

    def books_borrowed_count(self):
        return BorrowRecord.objects.filter(
            user=self.user,
            status='borrowed'
        ).count()

    def can_borrow_more_books(self):
        return self.books_borrowed_count() < self.max_books_allowed


class BorrowRecord(models.Model):
    STATUS_CHOICES = [
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='borrow_records')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='borrow_records')

    # Dates
    borrow_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)

    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='borrowed')
    renewal_count = models.PositiveIntegerField(default=0)
    max_renewals = models.PositiveIntegerField(default=2)

    # Admin fields
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='issued_records')
    returned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='received_records')

    # Notes
    issue_notes = models.TextField(blank=True)
    return_notes = models.TextField(blank=True)

    # Fine calculation
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fine_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['-borrow_date']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['book', 'status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} borrowed {self.book.title}"

    def save(self, *args, **kwargs):
        # Set default due date (14 days from borrow date)
        if not self.due_date:
            self.due_date = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    def is_overdue(self):
        if self.status == 'returned':
            return False
        return timezone.now() > self.due_date

    def days_overdue(self):
        if not self.is_overdue():
            return 0
        return (timezone.now() - self.due_date).days

    def can_renew(self):
        return (self.renewal_count < self.max_renewals and
                self.status == 'borrowed' and
                not self.is_overdue())

    def calculate_fine(self, daily_fine=1.00):
        """Calculate fine for overdue books"""
        if self.is_overdue():
            days_late = self.days_overdue()
            return days_late * daily_fine
        return 0.00


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reservations')
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notified = models.BooleanField(default=False)

    class Meta:
        ordering = ['reservation_date']
        unique_together = ['user', 'book', 'status']  # Prevent duplicate active reservations

    def __str__(self):
        return f"{self.user.get_full_name()} reserved {self.book.title}"

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            self.expiry_date = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expiry_date


class Notification(models.Model):
    TYPE_CHOICES = [
        ('due_reminder', 'Due Reminder'),
        ('overdue', 'Overdue Notice'),
        ('reservation_ready', 'Reservation Ready'),
        ('return_confirmation', 'Return Confirmation'),
        ('fine_notice', 'Fine Notice'),
        ('general', 'General Notification'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')

    # Status
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Related objects
    borrow_record = models.ForeignKey(BorrowRecord, on_delete=models.CASCADE,
                                      null=True, blank=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.get_full_name()}: {self.title}"


# Signal handlers to create user profiles and update book availability
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()


@receiver(post_save, sender=BorrowRecord)
def update_book_availability_on_borrow(sender, instance, created, **kwargs):
    if created and instance.status == 'borrowed':
        book = instance.book
        book.available_copies = max(0, book.available_copies - 1)
        if book.available_copies == 0:
            book.status = 'borrowed'
        book.save()


@receiver(post_save, sender=BorrowRecord)
def update_book_availability_on_return(sender, instance, created, **kwargs):
    if not created and instance.status == 'returned':
        book = instance.book
        book.available_copies += 1
        if book.available_copies > 0 and book.status == 'borrowed':
            book.status = 'available'
        book.save()