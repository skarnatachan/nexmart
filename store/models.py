from django.db import models
from category.models import Category
from django.utils.text import slugify


class Product(models.Model):
    SIZE_SMALL = "S"
    SIZE_MEDIUM = "M"
    SIZE_LARGE = "L"
    SIZE_EXTRA_LARGE = "XL"
    SIZE_CHOICES = [
        (SIZE_SMALL, "Small"),
        (SIZE_MEDIUM, "Medium"),
        (SIZE_LARGE, "Large"),
        (SIZE_EXTRA_LARGE, "Extra Large"),
    ]

    COLOR_CHOICES = [
        ("black", "Black"),
        ("white", "White"),
        ("gray", "Gray"),
        ("navy", "Navy"),
        ("red", "Red"),
    ]

    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image = models.ImageField(upload_to='images/products', blank=True,null=True)
    size = models.CharField(max_length=2, choices=SIZE_CHOICES, blank=True)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
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

    class Meta:
        verbose_name_plural = "Products"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=100)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.product.product_name}"

    class Meta:
        ordering = ['-created_at']
