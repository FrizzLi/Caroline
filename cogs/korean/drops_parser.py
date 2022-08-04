from glob import glob

paths = glob("vocab5/*/*")
titles = [full_path for full_path in paths]

for title in titles:
    eng_exp = []
    kor_exp = []
    fii = open(title, encoding="utf-8")
    english = False
    korean = False
    for line in fii:
        if line.startswith("Related topics"):
            break
        if line.endswith(".svg\n"):
            continue
        if line.startswith("KOREAN"):
            english = True
            continue
        if english:
            eng_exp.append(line.rstrip())
            korean = True
            english = False
            continue
        if korean:
            kor_exp.append(line.rstrip())
            korean = False
            english = True

    fii = open(title, "w", encoding="utf-8")
    for eng, kor in zip(eng_exp, kor_exp):
        fii.write(eng + " - " + kor + "\n")
