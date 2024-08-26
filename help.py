from datetime import datetime

# Get today's date
today = datetime.today()

# Get the date of the same day last year
last_year_today = today.replace(year=today.year - 1)

# Format the dates as dd/mm/yy
today_formatted = today.strftime("%d/%m/%y")
last_year_today_formatted = last_year_today.strftime("%d/%m/%y")
print(type(last_year_today))
# Print the formatted dates
print(f"Today's date: {today_formatted}")
print(f"Last year's same day: {last_year_today_formatted}")

# Compare the dates
if today > last_year_today:
    print(f"Today ({today_formatted}) is after last year's same day ({last_year_today_formatted}).")
elif today < last_year_today:
    print(f"Today ({today_formatted}) is before last year's same day ({last_year_today_formatted}).")
else:
    print(f"Today ({today_formatted}) is the same as last year's same day ({last_year_today_formatted}).")

