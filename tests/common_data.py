company = {
    "name": "Dummy company name",
    "nip": "123-123-123",
    "regon": "348509723045",
    "street": "Street no",
    "city": "Dummy city",
    "code": "333"
}

program = {
    "semester_no": 2,
    "school_year": "2022/2023",
    "fruitVeg_price": 1.0,
    "dairy_price": 2.0,
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "dairy_min_per_week": 2,
    "fruitVeg_min_per_week": 3,
    "dairy_amount": 12,
    "fruitVeg_amount": 21
}

school_data = {
    "nick": "My dummy school"
}

annex_data = {
    "validity_date": "2023-12-07",
    "fruitVeg_products": 10,
    "dairy_products": 1
}

week_data = {
    "start_date": "2023-12-01",
    "end_date": "2023-12-16",
    "week_no": 1
}


def get_program_data(company_id):
    program["company_id"] = company_id
    return program
