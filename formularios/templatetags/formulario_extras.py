from django import template

register = template.Library()

@register.filter
def get_item_dynamic(dictionary, key, index=0):
    if not isinstance(dictionary, dict):
        return ""
    full_key = f"q_{key}_{index}"
    return dictionary.get(full_key, "")

@register.filter
def add_index(value, index):
    return f"{value}_{index}"

@register.filter
def add_str(value, arg):
    return str(value) + str(arg)

@register.filter
def has_data_for_index(dictionary, question_id_and_index):
    # This filter check if any key in the dictionary starts with q_{question_id}_{index}
    if not isinstance(dictionary, dict):
        return False
    prefix = f"q_{question_id_and_index}"
    for key in dictionary.keys():
        if key.startswith(prefix):
            return True
    return False

@register.filter
def get_value(dictionary, key):
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")

@register.filter
def split(value, arg):
    return value.split(arg)

@register.filter
def trim(value):
    return value.strip()

