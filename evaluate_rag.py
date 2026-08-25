from pdf_reader import retrieve_documents


test_questions = [
    {
        "question": "How much total funding did AI-focused healthcare startups secure in Q1 2025, and what percentage of all digital health funding did this represent?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 13
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
        "expected_page": 8
    },
    {
        "question": "What specific statistical detail does the report provide to demonstrate the vulnerability of \"anonymized\" healthcare datasets to re-identification?",
        "expected_source": "AI_Healthcare_Sector_Market_Report.pdf",
        "expected_page": 8
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
        "expected_page": 1
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


def evaluate_hit_at_3():
    hits = 0

    for test in test_questions:
        results = retrieve_documents(
            test["question"],
            n_results=3
        )

        retrieved_metadata = results["metadatas"][0]

        hit = any(
            metadata["source"] == test["expected_source"]
            and metadata["page"] == test["expected_page"]
            for metadata in retrieved_metadata
        )

        if hit:
            hits += 1
            print(f"PASS: {test['question']}")
        else:
            print(f"\nFAIL: {test['question']}")
            print(
                f"Expected: {test['expected_source']}, "
                f"Page {test['expected_page']}"
            )

            print("Retrieved:")
            for i, metadata in enumerate(retrieved_metadata, start=1):
                print(
                    f"  {i}. {metadata['source']}, "
                    f"Page {metadata['page']}"
                )

    score = hits / len(test_questions)

    print(f"\nHit@3: {score:.2%}")


if __name__ == "__main__":
    evaluate_hit_at_3()