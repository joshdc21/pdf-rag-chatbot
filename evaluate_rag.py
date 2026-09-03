from pdf_reader import retrieve_documents_supabase
from supabase_client import supabase


# ============================================================
# TEST USER LOGIN
# ============================================================

TEST_EMAIL = "email@example.com"
TEST_PASSWORD = "emailpassword"

auth_response = supabase.auth.sign_in_with_password({
    "email": TEST_EMAIL,
    "password": TEST_PASSWORD
})

if not auth_response.user:
    raise RuntimeError("Supabase authentication failed")

print(f"Authenticated as: {auth_response.user.email}")
print(f"User ID: {auth_response.user.id}")


# ============================================================
# TEST QUESTIONS
# ============================================================

test_questions = [
    {
        "question": "How much total funding did AI-focused healthcare startups secure in Q1 2025, and what percentage of all digital health funding did this represent?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 11
    },
    {
        "question": "How does the report define the concept and scope of \"Artificial Intelligence (AI) in healthcare\"?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 1
    },
    {
        "question": "Explain why the automation of administrative tasks (such as scheduling and billing) is considered a \"catalyst\" for improving patient care, rather than just a cost-saving measure?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 2
    },
    {
        "question": "How are the concept of \"rapid healthcare data expansion\" and the concept of \"data privacy/bias risks\" dynamically related to the market's growth?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 10
    },
    {
        "question": "What specific statistical detail does the report provide to demonstrate the vulnerability of \"anonymized\" healthcare datasets to re-identification?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 10
    },
    {
        "question": "According to the \"Introduction to UI/UX Design\" article, what is its exact publication date, and what is the specific university affiliation of its author, Nasrullah Hamidli?",
        "expected_source": "Introduction_to_UI_UX_Design_Key_Concept.pdf",
        "expected_page": 1
    },
    {
        "question": "How does the article define the concept and functional purpose of \"wireframing\" in the design toolkit?",
        "expected_source": "Introduction_to_UI_UX_Design_Key_Concept.pdf",
        "expected_page": 11
    },
    {
        "question": "Explain why conducting user research and testing is critical to improving the Return on Investment (ROI) of a digital product's design.",
        "expected_source": "Introduction_to_UI_UX_Design_Key_Concept.pdf",
        "expected_page": 7
    },
    {
        "question": "How do the distinct concepts of \"UI design\" and \"UX design\" dynamically relate to and work with each other to determine the success of a digital product?",
        "expected_source": "Introduction_to_UI_UX_Design_Key_Concept.pdf",
        "expected_page": 2
    },
    {
        "question": "What six specific emerging technological and design trends does the article explicitly state will shape the future of UI/UX design?",
        "expected_source": "Introduction_to_UI_UX_Design_Key_Concept.pdf",
        "expected_page": 13
    },
    {
        "question": "According to the article \"Pancasila as a Philosophical System,\" in what year did Pancasila officially begin serving as the basic principles and ideological framework to help the Indonesian state develop?",
        "expected_source": "Pancasila.pdf",
        "expected_page": 1
    },
    {
        "question": "Explain how studying philosophy systematically divides its core problem areas, and what central questions correspond to each branch.",
        "expected_source": "Pancasila.pdf",
        "expected_page": 4
    },
    {
        "question": "How do the concepts of Pancasila as an \"organic, hierarchical unity\" and the status of its individual \"principles\" relate to each other?",
        "expected_source": "Pancasila.pdf",
        "expected_page": 5
    },
    {
        "question": "How does the article define Sastrapradetdja’s concept of \"ideology\" when viewed in a narrow sense?",
        "expected_source": "Pancasila.pdf",
        "expected_page": 3
    },
    {
        "question": "What specific metaphor did Muhammad Yamin use in 1958 to reject the idea that the five principles of Pancasila are merely a random collection of good things?",
        "expected_source": "Pancasila.pdf",
        "expected_page": 5
    },
]


# ============================================================
# EVALUATION
# ============================================================

def evaluate_hit_at_3():
    hits = 0

    for i, test in enumerate(test_questions, start=1):

        print(f"\n{'=' * 70}")
        print(f"Question {i}/{len(test_questions)}")
        print(test["question"])

        results = retrieve_documents_supabase(
            test["question"],
            n_results=1
        )

        hit = any(
            result.get("source") == test["expected_source"]
            and result.get("page") == test["expected_page"]
            for result in results
        )

        if hit:
            hits += 1
            print("PASS")

        else:
            print("FAIL")
            print(
                f"Expected: {test['expected_source']}, "
                f"Page {test['expected_page']}"
            )

            if not results:
                print("Retrieved: NOTHING")
            else:
                print("Retrieved:")
                for rank, result in enumerate(results, start=1):
                    print(
                        f"  {rank}. "
                        f"{result.get('source')}, "
                        f"Page {result.get('page')}, "
                        f"Similarity: {result.get('similarity')}"
                    )

    score = hits / len(test_questions)

    print(f"\n{'=' * 70}")
    print(f"Hit@3: {hits}/{len(test_questions)} = {score:.2%}")


if __name__ == "__main__":
    evaluate_hit_at_3()