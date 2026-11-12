from django.db import models
from category.models import Category
from django.utils.text import slugify


class Size(models.Model):
    code = models.CharField(max_length=10, unique=True)
    label = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['display_order', 'id']


class Color(models.Model):
    code = models.CharField(max_length=20, unique=True)
    label = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.label

    class Meta:
        ordering = ['display_order', 'id']


class Product(models.Model):
    product_name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=200, unique=True, blank=True,
        help_text="Leave blank to auto-generate a unique slug for this variant.",
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.ImageField(upload_to='images/products', blank=True,null=True)
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name='products')
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.product_name)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        return slug

    def variants(self):
        return Product.objects.filter(
            product_name=self.product_name, is_available=True
        ).select_related('category', 'size', 'color')

    class Meta:
        verbose_name_plural = "Products"
        unique_together = ('product_name', 'size', 'color')


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.product.product_name}"

    class Meta:
        ordering = ['-created_at']

class Tax(models.Model):
    tax_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tax_value}"
