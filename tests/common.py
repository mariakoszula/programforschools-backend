def all_fields_to_marge_are_in_file(file_name, **fields):
    import docx2txt
    text = docx2txt.process(file_name)
    for value in fields.values():
        assert str(value) in text and f"value: {value} not found in {text}"

