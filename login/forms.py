from django import forms
from .models import LostFoundItem, Claim

class LostFoundItemForm(forms.ModelForm):
    class Meta:
        model = LostFoundItem
        fields = ["title", "description", "photo", "status", "found_lat", "found_lng", "found_at", "claim_question", "correct_answer"]
        widgets = {
            "found_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

class ClaimForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ["answer_text"]
        widgets = {
            "answer_text": forms.Textarea(attrs={"rows": 3, "placeholder": "Your verification answer..."}),
        }