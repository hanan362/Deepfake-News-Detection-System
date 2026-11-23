# Data flow diagrams

## Level 0: context

```mermaid
flowchart LR
    U["User"] -->|"article text, image, account details"| S(("Deepfake News Detection System"))
    S -->|"result, indicators, PDF report, history"| U
    S <-->|"news page fetch; claim words to Wikipedia"| W["Web sites<br/>news pages, Wikipedia"]
    A["Administrator"] -->|"role changes, feedback review"| S
    S -->|"statistics, audit log, model status"| A
    D[("Public datasets<br/>Hugging Face")] -->|"training data, downloaded once by the training script"| S
```

## Level 1

```mermaid
flowchart TB
    U["User"]
    A["Administrator"]

    P1["1 Authenticate<br/>register, log in, reset, log out"]
    P2["2 Analyse text, news address<br/>and evidence"]
    P3["3 Analyse image, video<br/>and image with text"]
    P4["4 History and reports"]
    P5["5 Administer"]
    P6["6 Train text model<br/>offline script"]

    D1[("D1 Database<br/>users, roles, submissions,<br/>analyses, predictions,<br/>feedback, audit log")]
    D2[("D2 File storage<br/>uploaded images and videos,<br/>heatmaps, frame thumbnails,<br/>avatars")]
    D3[("D3 Model files<br/>checkpoint, metadata,<br/>registry, metrics")]
    D4[("D4 Datasets<br/>raw, processed, manifests")]

    U -->|"credentials"| P1
    P1 -->|"token"| U
    P1 <-->|"accounts, revoked tokens, reset tokens"| D1

    U -->|"text and optional headline"| P2
    P2 -->|"verdict, probabilities, term contributions, limitations"| U
    P2 -->|"read model"| D3
    P2 -->|"submission, analysis, text prediction"| D1

    U -->|"image file"| P3
    P3 -->|"indicators, heatmap, limitations"| U
    P3 -->|"store image and heatmap"| D2
    P3 -->|"submission, analysis, image prediction"| D1

    U -->|"history query, report request, delete"| P4
    P4 -->|"list, detail, PDF"| U
    P4 <-->|"owner-only reads and deletes"| D1
    P4 <-->|"owner-only files"| D2

    A -->|"user changes, review decisions"| P5
    P5 -->|"counts, audit log, model status"| A
    P5 <-->|"users, feedback, audit log"| D1
    P5 -->|"read registry"| D3

    D4 -->|"download, clean, split"| P6
    P6 -->|"checkpoint, metrics, registry, manifest"| D3
    P6 -->|"manifest"| D4
```

## Notes

- Process 6 is not part of the running server. It is a script (`ai_models/training/train_text_baseline.py`) that writes the files process 2 reads.
- Process 2 (text) and process 3 (image) never send the submitted content to any outside service. The models run inside the backend process.
- The later modules are drawn in the Level 1 diagram as part of processes 2 and 3 for brevity. They differ in what leaves the server: a news web address is fetched from its own site; the evidence check sends the main words of each claim to Wikipedia (and to a fact-check search when a key is set); the video, image-text and evidence models are downloaded from Hugging Face on first use. An uploaded video is stored under a random name, read only by its owner and deleted with the analysis.
