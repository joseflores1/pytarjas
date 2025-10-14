# tests/helper.py
"""
Helper functions to help with testing, with functionalities such as:
- Check if a string is a valid UUID version 4
"""
import re

def is_valid_uuid4(uuid: str) -> bool:
    """
    Check by REGEX if a string is a valid uuid 4 version

    Args:
        - uuid: the string to be checked

    Return:
        - True if the string arg is a valid uuid 4 version, else False
    """
    uuid_v4_regex=re.compile(
        r'^[0-9a-fA-F]{8}-'
        r'[0-9a-fA-F]{4}-'
        r'4[0-9a-fA-F]{3}-'
        r'[89abAB][0-9a-fA-F]{3}-'
        r'[0-9a-fA-F]{12}$'
    )   
    return bool(uuid_v4_regex.fullmatch(uuid))