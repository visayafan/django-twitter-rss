from twitter.views import format_status, format_title

d = format_status('https://twitter.com/KenWong_/status/1034722889893732352')
print(d)
t = format_title(d)
print('-'*100)
print(t)
