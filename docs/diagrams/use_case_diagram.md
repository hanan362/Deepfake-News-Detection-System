# Use case diagram

Actors are the visitor (not signed in), the signed-in user and the administrator. An administrator is also a user. Use cases drawn with a dashed border are **not built**.

```mermaid
flowchart LR
    V([Visitor])
    U([Signed-in user])
    A([Administrator])
    U -. is a .-> V
    A -. is a .-> U

    subgraph Public["Public"]
        UC1["Read landing, methodology and about pages"]
        UC2["View model status and measured results"]
        UC3["Register an account"]
        UC4["Log in"]
        UC5["Reset a forgotten password"]
    end

    subgraph Analysis["Analysis"]
        UC6["Analyse the writing of a news article"]
        UC7["Get forensic indicators for an image"]
        UC8["Read a result with its limitations"]
        UC9["Download a PDF report"]
        UC10["Browse, filter and delete history"]
        UC11["See personal dashboard"]
        UC12["Send feedback or report a wrong result"]
        UC21["Analyse a news web address"]
        UC22["Check a claim against evidence"]
        UC23["Check an image against its headline"]
        UC24["Analyse a video"]
    end

    subgraph Account["Account"]
        UC13["Edit profile and avatar"]
        UC14["Change password"]
        UC15["Log out"]
    end

    subgraph Admin["Administration"]
        UC16["Manage users: role, enable, disable"]
        UC17["Review feedback"]
        UC18["Read the audit log"]
        UC19["See system statistics"]
        UC20["See model registry"]
    end

    subgraph Planned["Not built"]
        P1["Detect generated or edited images"]
        P2["Learn motion and audio in video"]
    end

    V --> UC1 & UC2 & UC3 & UC4 & UC5
    U --> UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC13 & UC14 & UC15 & UC21 & UC22 & UC23 & UC24
    A --> UC16 & UC17 & UC18 & UC19 & UC20
    U -.-> P1 & P2
    UC8 -. extends .-> UC9
    UC6 -. includes .-> UC8
    UC7 -. includes .-> UC8
    style P1 stroke-dasharray: 5 5
    style P2 stroke-dasharray: 5 5
```

## Rules that the use cases rely on

- A user sees only their own analyses, images and heatmaps. An administrator gets the same `404` for other people's analyses, because admins work from counts and not from content.
- An administrator cannot demote or disable their own account.
- The result of every analysis shows its limitations text.
