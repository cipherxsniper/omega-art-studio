import subprocess

url = "https://buy.stripe.com/test_fZu00i8YLgbP2kXckoa7C00"

print("OPENING STRIPE TEST LINK:")
print(url)

# Termux open browser
subprocess.run(["termux-open-url", url])
