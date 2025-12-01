from django import forms
from .models import PantryItem

class PantryItemForm(forms.ModelForm):
    UNIT_CHOICES = PantryItem.UNIT_CHOICES  # directly use model choices
    unit= forms.ChoiceField(choices=UNIT_CHOICES)
    class Meta:
        model = PantryItem
        fields = ['ingredient_name', 'qty', 'unit', 'expire_date', 'category']
        widgets = {
            'category': forms.Select(choices=PantryItem.CATEGORY_CHOICES),
            'expire_date': forms.DateInput(attrs={'type': 'date'}),
        }
