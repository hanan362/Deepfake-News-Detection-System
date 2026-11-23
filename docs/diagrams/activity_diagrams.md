# Activity diagrams

## 1. Analyse a news article (text)

The web page blocks submission of text that is too short, too long or in Arabic script. The API itself accepts such text and answers `Unverified` with the reason, so the later steps in the diagram matter for direct API use.

```mermaid
flowchart TD
    start([Start]) --> in["User enters article text and an optional headline"]
    in --> client{"Client check: at least 60 words,<br/>at most 50,000 characters,<br/>not Arabic script, model available?"}
    client -- no --> fix["Analyse button stays disabled<br/>and the reason is shown"]
    client -- yes --> send["POST /analysis/text"]
    send --> auth{"Valid token?"}
    auth -- no --> e401["401 error envelope"]
    auth -- yes --> size{"Longer than 50,000 characters?"}
    size -- yes --> e413["413 error"]
    size -- no --> script{"Mostly Arabic-script text?"}
    script -- yes --> unv1["Result: Unverified, reason unsupported language"]
    script -- no --> words{"At least 60 words?"}
    words -- no --> unv2["Result: Unverified, reason too short"]
    words -- yes --> model{"Model file present and built with<br/>the installed scikit-learn?"}
    model -- no --> e503["503 error with the fix"]
    model -- yes --> score["Clean text, TF-IDF, logistic regression:<br/>probability fake and real"]
    score --> thr{"Either probability at or above 0.80?"}
    thr -- fake --> fake["Likely Fake"]
    thr -- real --> real["Likely Real"]
    thr -- neither --> unv3["Unverified, reason low confidence"]
    fake --> explain["Compute exact term contributions"]
    real --> explain
    unv3 --> explain
    explain --> store["Save submission, analysis and text prediction"]
    unv1 --> store
    unv2 --> store
    store --> show["Show result, probabilities, explanation and limitations"]
    show --> endn([End])
    e401 --> endn
    e413 --> endn
    e503 --> endn
    fix --> endn
```

## 2. Analyse an image

```mermaid
flowchart TD
    start([Start]) --> pick["User chooses a file"]
    pick --> c1{"Client check:<br/>JPEG, PNG or WEBP, at most 10 MB?"}
    c1 -- no --> msg["Show message"]
    c1 -- yes --> up["POST /analysis/image"]
    up --> a{"Valid token?"}
    a -- no --> e401["401"]
    a -- yes --> sz{"Larger than the size limit?"}
    sz -- yes --> e413["413"]
    sz -- no --> content{"Content decodes as JPEG, PNG or WEBP<br/>and within 40 million pixels?"}
    content -- no --> e415["415 unsupported or unsafe image"]
    content -- yes --> ela["Re-save as JPEG at quality 90,<br/>measure difference per pixel and per block"]
    ela --> meta["Read metadata: camera, software, dates"]
    meta --> heat["Draw the Error Level Analysis map"]
    heat --> save["Store image and map under random names;<br/>save submission, analysis, image prediction"]
    save --> res["Result: Indicators Only, measurements,<br/>observations, limitations. No confidence value"]
    res --> endn([End])
    e401 --> endn
    e413 --> endn
    e415 --> endn
    msg --> endn
```

## 3. Password reset

```mermaid
flowchart TD
    s([Start]) --> f["User enters e-mail on Forgot password"]
    f --> r["POST /auth/forgot-password"]
    r --> same["Same answer whether or not the account exists"]
    same --> exists{"Account exists and active?"}
    exists -- yes --> tok["Create random token, store its SHA-256 and an expiry"]
    exists -- no --> idle["Nothing stored"]
    tok --> deliver{"EXPOSE_RESET_TOKEN is true?"}
    deliver -- yes --> dev["Token is returned in the response (development only)"]
    deliver -- no --> none["No e-mail service exists, so an administrator must provide a way to deliver the token"]
    dev --> use["User opens Reset password with the token and a new password"]
    use --> chk{"Token known, unused, not expired, password strong enough?"}
    chk -- no --> bad["400 or 422"]
    chk -- yes --> done["Set new password, mark token used, end all earlier sessions"]
    done --> e([End])
    bad --> e
    idle --> e
    none --> e
```

## 4. Administer a user

```mermaid
flowchart TD
    s([Start]) --> l["Admin opens Users"]
    l --> pick["Choose a user and a change: role or enabled"]
    pick --> self{"Is it the admin's own account<br/>being demoted or disabled?"}
    self -- yes --> deny["400 SELF_LOCKOUT"]
    self -- no --> apply["Apply the change"]
    apply --> log["Write an audit log entry"]
    log --> ok["Show updated list"]
    ok --> e([End])
    deny --> e
```
