from django.db import migrations, models
import django.db.models.deletion


OLD_SIZES = [
    ("S", "Small", 0),
    ("M", "Medium", 1),
    ("L", "Large", 2),
    ("XL", "Extra Large", 3),
]

OLD_COLORS = [
    ("black", "Black", 0),
    ("white", "White", 1),
    ("gray", "Gray", 2),
    ("navy", "Navy", 3),
    ("red", "Red", 4),
    ("blue", "Blue", 5),
]


def seed_sizes_and_colors(apps, schema_editor):
    Size = apps.get_model("store", "Size")
    Color = apps.get_model("store", "Color")
    for code, label, order in OLD_SIZES:
        Size.objects.get_or_create(code=code, defaults={"label": label, "display_order": order})
    for code, label, order in OLD_COLORS:
        Color.objects.get_or_create(code=code, defaults={"label": label, "display_order": order})


def populate_product_fks(apps, schema_editor):
    Product = apps.get_model("store", "Product")
    Size = apps.get_model("store", "Size")
    Color = apps.get_model("store", "Color")
    sizes_by_code = {s.code: s for s in Size.objects.all()}
    colors_by_code = {c.code: c for c in Color.objects.all()}
    for product in Product.objects.all():
        product.size_new = sizes_by_code[product.size]
        product.color_new = colors_by_code[product.color]
        product.save(update_fields=["size_new", "color_new"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0007_add_blue_color_choice"),
    ]

    operations = [
        migrations.CreateModel(
            name="Size",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=10, unique=True)),
                ("label", models.CharField(max_length=50)),
                ("display_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["display_order", "id"]},
        ),
        migrations.CreateModel(
            name="Color",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("label", models.CharField(max_length=50)),
                ("display_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["display_order", "id"]},
        ),
        migrations.RunPython(seed_sizes_and_colors, noop_reverse),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="product",
            name="size_new",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="products_new", to="store.size"),
        ),
        migrations.AddField(
            model_name="product",
            name="color_new",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="products_new", to="store.color"),
        ),
        migrations.RunPython(populate_product_fks, noop_reverse),
        migrations.RemoveField(model_name="product", name="size"),
        migrations.RemoveField(model_name="product", name="color"),
        migrations.RenameField(model_name="product", old_name="size_new", new_name="size"),
        migrations.RenameField(model_name="product", old_name="color_new", new_name="color"),
        migrations.AlterField(
            model_name="product",
            name="size",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="store.size"),
        ),
        migrations.AlterField(
            model_name="product",
            name="color",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="store.color"),
        ),
        migrations.AlterUniqueTogether(
            name="product",
            unique_together={("product_name", "size", "color")},
        ),
    ]
