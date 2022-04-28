def bahamut_font(text):
    key = ["[ABCEDFGHIJKLMNO", "PQRSTUVWXYZabcde", "fghijklmnopqrstu", "vwxyz-0123456789", ".,?!\'\":;×/()*—]"]
    key_dict = {}
    r_dict = {}
    for line in key:
        for char in line:
            key_dict[char] = [line.index(char), key.index(line)]
    print(type(key_dict))
    print(type(r_dict))
    words = text.split()
    for word in words:
        r_dict[word] = {}
        for c in word:
            r_dict[word][c] = key_dict[c]
    return r_dict

r = bahamut_font("Adding an item to the dictionary is done by using a new index key and assigning a value to it:")
print(r)
