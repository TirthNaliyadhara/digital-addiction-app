"""One-shot script to fix the broken emoji bytes in app.py lines 1634-1635."""

with open(r'app.py', 'rb') as f:
    content = f.read()

# Broken sequences
old1 = 'st.metric("\ufffd Total Screen Time"'.encode('utf-8')
old2 = 'st.metric("\ufffd\U0001f4c5 Avg Screen Time"'.encode('utf-8')

# Clean replacements
new1 = 'st.metric("\U0001f4fa Total Screen Time"'.encode('utf-8')   # 📺
new2 = 'st.metric("\U0001f4ca Avg Screen Time / Day"'.encode('utf-8')  # 📊

print('old1 found:', old1 in content)
print('old2 found:', old2 in content)

content = content.replace(old1, new1)
content = content.replace(old2, new2)

with open(r'app.py', 'wb') as f:
    f.write(content)

print('Done.')
