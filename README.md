# FINDBACK: Web-Based Object Recovery and Tracking System

> **College Mini-Project | 5th-Semester B.Tech Artificial Intelligence and Data Science**  
> An intelligent, privacy-first, web-based platform designed to automate and streamline lost-and-found recovery across university campuses, hostels, libraries, and public institutions.

---

## 1. Project Overview & Vision

Most conventional lost-and-found systems are passive notice boards or simple CRUD lists that require manual browsing, provide zero verification security, and expose personal contact details. 

**FindBack** changes this paradigm by integrating:
1. **Automated NLP Matching Engine**: Uses **TF-IDF (Term Frequency-Inverse Document Frequency)** and **Cosine Similarity** augmented with domain synonym expansion and weighted multi-attribute heuristics (Description 50%, Category 20%, Location 20%, Date 10%).
2. **Privacy-Preserving Ownership Verification**: Sensitive identifying characteristics are never published publicly. Claimants must provide distinguishing proof that is cross-checked against secretly logged markers before contact details are unlocked.
3. **Audited 5-Stage Status Progression**: Every item moves through an immutable, timestamped lifecycle:
   $$\text{Reported} \longrightarrow \text{Matched} \longrightarrow \text{Claim Requested} \longrightarrow \text{Verified} \longrightarrow \text{Returned}$$
4. **Smart Preventive QR Recovery Tags**: Pre-registered belongings receive unique QR tags. When scanned by a finder, they open an anonymous recovery portal without exposing the owner's phone or email.
5. **Real-Time Admin Telemetry**: Live metric calculations (Recovery rate, average turnaround time, category loss distribution, location hotspot clustering) powered by Chart.js.

---

## 2. Technical Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js 4.4 |
| **Backend** | Python 3.11, Flask 3.1, Werkzeug (PBKDF2 SHA-256 Hashing) |
| **Database** | SQLite 3 with Write-Ahead Logging (`WAL`) and strict Foreign Key constraints |
| **NLP & AI Matching** | `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`), `numpy`, `pandas` |
| **QR Code Engine** | `qrcode` (High error correction level `H`), `Pillow` (PIL) |
| **Environment** | Fully local execution — zero external paid APIs, zero permanent internet requirement |

---

## 3. System Architecture & Directory Structure

```
FindBack/
├── app/
│   ├── __init__.py                 # Application factory & Jinja context processors
│   ├── models.py                   # Relational database schema, connection & audit logging
│   ├── routes/
│   │   ├── auth.py                 # Registration, login, session, user profiles
│   │   ├── items.py                # Reporting lost & found, item view, browse & filter
│   │   ├── matches.py              # AI match suggestions, side-by-side comparison
│   │   ├── claims.py               # Ownership claim submission, verification & handover
│   │   ├── qr.py                   # QR registration, download, public anonymous scan
│   │   ├── admin.py                # Telemetry dashboard, user RBAC, item moderation
│   │   └── api.py                  # Notifications read & dynamic stats endpoints
│   ├── services/
│   │   ├── auth_service.py         # Password hashing & route access decorators
│   │   ├── qr_service.py           # High-resolution QR asset generation
│   │   └── notification_service.py # In-app notification dispatcher
│   ├── matching/
│   │   └── engine.py               # TF-IDF, synonym expansion & weighted scoring engine
│   ├── templates/                  # 18 Modular, responsive Jinja2 templates
│   │   ├── base.html               # Master layout with navbar & notification bell
│   │   ├── index.html              # Modern SaaS landing page with live counters
│   │   ├── auth/                   # login.html, register.html, profile.html
│   │   ├── items/                  # dashboard.html, report_lost.html, report_found.html, view_lost.html, view_found.html, my_reports.html, browse.html
│   │   ├── matches/                # view_matches.html, match_detail.html
│   │   ├── claims/                 # submit_claim.html, my_claims.html, received_claims.html, review_claim.html
│   │   ├── qr/                     # register_qr.html, view_qr.html, my_codes.html, scan_contact.html, scan_success.html
│   │   └── admin/                  # dashboard.html, users.html, items.html, claims.html
│   └── static/
│       ├── css/styles.css          # Custom enterprise design system
│       └── js/main.js              # Client-side notifications, preview & printing
├── uploads/                        # Uploaded item photographs & generated QR codes
├── instance/                       # SQLite database instance (findback.db)
├── config.py                       # Configuration parameters, weights & thresholds
├── run.py                          # Application entry point
├── seed_data.py                    # Complete college presentation demonstration dataset
├── test_matching.py                # Unit test suite for matching algorithms
├── test_integration.py             # Automated end-to-end user journey test suite
├── requirements.txt                # Python package dependencies
└── README.md                       # Comprehensive project documentation
```

---

## 4. Intelligent Matching Algorithm

### Mathematical Formulation

The matching engine processes textual descriptions into numerical vectors using **TF-IDF**:

$$\text{TF}(t, d) = \frac{f_{t,d}}{\sum_{t' \in d} f_{t',d}}$$

$$\text{IDF}(t, D) = \log\left(\frac{1 + |D|}{1 + |\{d \in D : t \in d\}|}\right) + 1$$

$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$

Cosine similarity between the lost item vector $\mathbf{v}_{\text{lost}}$ and found item vector $\mathbf{v}_{\text{found}}$ evaluates linguistic overlap:

$$\text{Sim}_{\text{desc}} = \frac{\mathbf{v}_{\text{lost}} \cdot \mathbf{v}_{\text{found}}}{\|\mathbf{v}_{\text{lost}}\|_2 \|\mathbf{v}_{\text{found}}\|_2} \times 100$$

### Combined Multi-Attribute Formula (Project Synopsis Weights)

$$\text{Total Score} = (0.50 \times S_{\text{desc}}) + (0.20 \times S_{\text{cat}}) + (0.20 \times S_{\text{loc}}) + (0.10 \times S_{\text{date}})$$

Where:
- $S_{\text{desc}}$: TF-IDF Cosine Similarity with synonym expansion and attribute reinforcement.
- $S_{\text{cat}}$: Exact category match = $100\%$; soft related category group = $70\%$; else $0\%$.
- $S_{\text{loc}}$: Overlap coefficient and Jaccard token similarity over campus location keywords (e.g., "Central Library 2nd Floor").
- $S_{\text{date}}$: Closeness curve ($100\%$ if same day, $90\%$ within 24h, $80\%$ within 48h, decaying smoothly).
- **Match Threshold**: $38.0\%$. Matches $\ge 70.0\%$ receive high-confidence visual alerts.

---

## 5. Quick Start & Execution Guide

### Prerequisites
- Python 3.11 installed locally.

### Step 1: Launch Application
Open a terminal in the project directory (`C:\Users\hp\.gemini\antigravity\scratch\FindBack`):
```bash
python run.py
```

### Step 2: Open in Web Browser
Navigate to:
```
http://127.0.0.1:5000
```

### Pre-Configured Demonstration Accounts

| Role | Name | Email | Password |
| :--- | :--- | :--- | :--- |
| **Administrator** | System Admin | `admin@findback.com` | `Admin@123` |
| **Student (Owner)** | Rahul Sharma | `rahul@campus.edu` | `User@123` |
| **Student (Finder)** | Sneha Patel | `sneha@campus.edu` | `User@123` |
| **Student (Member)** | Vikram Verma | `vikram@campus.edu` | `User@123` |

*(To re-seed clean demo data at any time, run: `python seed_data.py`)*

---

## 6. Step-by-Step College Demo Presentation Script

Follow this exact walkthrough to present the working application to your guide:

### Scene 1: The Problem & Landing Page
1. Open `http://127.0.0.1:5000`.
2. Highlight the **Live Telemetry Counters** (Total Reported, Returned, Recovery Rate, Users).
3. Demonstrate the **4-Stage Structured Workflow** and the **Search Catalog**.

### Scene 2: Lost Report & AI Matching (Rahul's Perspective)
1. Click **Sign In** with `rahul@campus.edu` / `User@123`.
2. Point out Rahul's personalized dashboard and the **AI Match Alert banner**.
3. Click on the Match: **Black Leather Bi-Fold Wallet $\leftrightarrow$ Black Men Leather Wallet** (**81.8% Match**).
4. Show the project guide the **4-Part Algorithm Weight Breakdown**:
   - Description NLP (50% wt): 69.6%
   - Category Match (20% wt): 100%
   - Location Context (20% wt): 85%
   - Date Closeness (10% wt): 100%
   - Algorithm Verdict tag: *Identical category, key matching descriptors, geographically correlated zone, reported within 24h*.

### Scene 3: Privacy-Preserving Claim Submission
1. On the match screen, click **Submit Ownership Claim**.
2. Notice that the finder's private distinguishing details are completely concealed!
3. Rahul enters his distinguishing proof:
   > *"Student ID ending in 4921, two Rs 100 notes and one Rs 50 note (total Rs 250)."*
4. Submit the claim. Notice that Found Item #1 status advances to **Claim Requested** on the 5-stage timeline stepper!
5. Sign out.

### Scene 4: Finder Verification & Approval (Sneha's Perspective)
1. Sign In as Finder: `sneha@campus.edu` / `User@123`.
2. Notice the in-app notification bell ring: *"New Ownership Claim Submitted"*.
3. Navigate to **My Activity $\rightarrow$ Received Claims**.
4. Click **Verify & Take Action**.
5. Show the project guide the **Evidence Cross-Verification Screen**:
   - **Ground Truth Box (Confidential)**: Sneha's private note logged when she found the wallet (*"Contains College ID ending in 4921 and Rs 250 in cash"*).
   - **Claimant Proof Box**: Rahul's submitted answer.
6. Click **Approve Claim & Verify Ownership**.
7. Notice: Mutual contact details (email and phone) are now securely unlocked for handover coordination, and the item status advances to **Verified**!

### Scene 5: Handover Completion & Statistics Update
1. After meeting, Sneha clicks **Confirm Handover & Mark Returned**.
2. Item status updates to **Returned** with a green checkmark on the timeline.
3. Sign out and log in as `admin@findback.com` / `Admin@123`.
4. Open the **Admin Panel**:
   - See the **Recovery Rate** increase.
   - Show the interactive **Category Doughnut Chart** and **Location Loss Hotspots Bar Chart** generated dynamically by Chart.js.
   - Inspect the **Real-Time Audit Log** showing every status transition with timestamps and actor names.

### Scene 6: Smart QR Preventive Feature
1. Log in as `vikram@campus.edu` / `User@123`.
2. Go to **Registered Belongings (QR)**.
3. View Vikram's registered **Hostel Room & Bike Keys**.
4. Demonstrate the printable QR code tag.
5. Click the public scan simulation link (`/qr/scan/<uuid>`).
6. Point out: The scanner sees *zero* personal phone/email numbers.
7. Fill out the finder contact form: *"Found near cafeteria bench, left with security"*.
8. Submit and verify that Vikram instantly receives an in-app notification!

---

## 7. Running Automated Test Suites

Verify algorithm mathematical validity and end-to-end integration:

```bash
# Unit Tests for Matching Algorithm (TF-IDF, synonyms, weights)
python test_matching.py

# End-to-End System Integration Tests (Full user journey & transitions)
python test_integration.py
```

Both test suites execute with 100% passing assertions.

---

## 8. College Mini-Project Submission Summary
- **Department**: Artificial Intelligence and Data Science Engineering
- **Semester**: 5th Semester
- **System**: FindBack (Object Recovery and Tracking System)
- **Status**: Production-Ready Working Prototype
