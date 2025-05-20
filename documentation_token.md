

How the Current System Works (Calendar Month Reset):
Reset Trigger: The token usage (token_usage_this_month) for all users resets at the beginning of each calendar month (e.g., February 1st, March 1st, etc.). The token_usage_month_start field in your database is updated to the first day of that new calendar month.
New User Sign-up:
When a new user signs up, their token_usage_this_month will effectively be 0, and token_usage_month_start will initially be NULL in the database.
The first time get_token_usage_status runs for this new user (e.g., when they make their first chat request):
The system sees that token_usage_month_start is not set to the current calendar month's start.
It initializes their token_usage_this_month to 0.
It sets their token_usage_month_start in the database to the first day of the current calendar month. For example, if they sign up on January 28th, their token_usage_month_start becomes January 1st.
Quota Availability for Late Sign-ups:
If a user signs up on January 28th:
Their token count for January starts at 0.
They have the full monthly token quota (defined by settings.USER_TOKEN_LIMIT_PER_MONTH) available to use for the remaining days of January (i.e., from January 28th to January 31st).
On February 1st, their token_usage_this_month will reset to 0 again, and they will get a fresh full monthly quota for February.
In essence:
The "limit starts from that day" in the sense that from the day they sign up, they can start using tokens against their monthly allowance.
This allowance is for the current calendar month. They get the full amount, regardless of whether they sign up on the 1st or the 28th of that month.
Everyone's limit resets on the 1st of the next calendar month.
This is a common and generally fair way to handle monthly quotas. It keeps the reset logic simple and consistent for all users.
Alternative (More Complex): Per-User Rolling 30-Day Window
If you wanted each user's "month" to start on their specific sign-up day (e.g., sign up Jan 28th, limit resets Feb 28th, then Mar 28th, etc.), this would be a "per-user rolling window." This is more complex to implement:
You'd need to store each user's individual current_period_start_date.
The reset logic would have to check if today is 30 days (or 1 month, considering varying month lengths) past their current_period_start_date.
This adds complexity in date calculations, especially around months with different numbers of days.
Conclusion:
The current implementation ensures that a user signing up late in the month still gets access to the full monthly token quota for the remainder of that calendar month. Then, they join the regular reset cycle with all other users on the 1st of the following month.
This approach should work well and is generally understood by users. No code changes are needed in backend/utils/usage_limiter.py for this behavior, as it already functions this way.
Let me know if this explanation aligns with your expectations or if you were envisioning the per-user rolling window!
