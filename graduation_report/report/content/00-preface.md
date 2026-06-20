# Preface

## Personal Background and Motivation

My journey into this thesis began with a question I asked myself as an ICT student who loves building products: how can computer vision solve real-world problems that matter? I was not content with toy datasets or classroom exercises — I wanted to work on something where the technology tangibly helps people.

This aspiration led me to join the MycoAI lab under the guidance of **Dr. Oanh Nguyen** from Hanoi University of Science and Technology (HUST), a researcher deeply dedicated to computer vision. Through Dr. Oanh, I was introduced to **Professor Duong Vu**, a data scientist based in the Netherlands who has spent years specializing in fungal classification and founded the MycoAI laboratory to bridge AI and mycology.

Rather than handing me a well-defined problem, they gave me something more valuable: access to a real fungal image dataset and a single open-ended question — *"What can you do to help a mycologist?"*

That question became my compass. I spent the early months not building models, but exploring the dataset, reading mycology literature, and speaking with domain experts to understand their workflow. Mycologists spend hours manually comparing colony photographs against reference books. A misidentification can delay research, misdirect treatment, or waste valuable lab resources. The bottleneck was not the microscope — it was the lookup.

Solving this required experimenting with a range of computer vision techniques: segmentation algorithms, embedding models, distance metrics, and retrieval strategies. Not every approach worked, and much of the early work was iteration — trying a method, measuring its real-world usefulness, and adapting. This thesis does not claim to be a heavy research contribution to computer vision, nor does it chase state-of-the-art benchmarks. It sits at the intersection of research and engineering: applying established CV techniques thoughtfully to a domain that genuinely needs them.

Crucially, success here is not defined by a 99% accuracy score. The goal is to assist a mycologist in two ways: identifying an unknown fungal species by visual similarity, and managing their unique, growing reference dataset. A tool that mycologists actually use is a better outcome than a model that sits on a leaderboard but never leaves the lab. The answer to that open-ended question became the MycoAI Retrieval system described in this thesis.

## Acknowledgments

I would like to express my sincere gratitude to **Dr. Oanh Nguyen** for her unwavering support throughout this project — for the guidance, the ideas, and the deep knowledge of computer vision techniques she shared with me at every stage. Her mentorship shaped not just the outcome of this thesis, but how I approach a problem as an engineer.

I am equally grateful to **Professor Duong Vu**, whose clear articulation of the project's requirements grounded this work in real mycologist needs. His domain expertise kept the system honest: every feature and every experiment was measured against the question of whether it actually helps the person in the lab.

## How to Read This Thesis

This report sits at the intersection of research and engineering. It is structured to reflect the full stack of the project, from algorithm to application:

- **Chapter 1** frames the problem, the dataset, and the rationale behind choosing a retrieval approach over classification.
- **Chapter 2** details the retrieval model pipeline: segmentation, embedding extraction, and nearest-neighbor search.
- **Chapter 3** presents the web application that wraps the model into a usable product.
- **Chapter 4** describes the Agentic Engineering methodology — how a multi-agent system was used to optimize the retrieval pipeline itself.
- **Chapter 5** concludes with reflections and directions for future work.

Readers interested primarily in the machine learning methodology should focus on Chapter 2. Readers interested in the product engineering and system design should focus on Chapter 3. The intersection of both — applying agents to automate ML experimentation — is covered in Chapter 4.

---

*Hanoi, June 2025*

## Writing Prompts

The following questions are meant as a guide for expanding this preface with your personal voice. They avoid duplicating the technical detail found in later chapters.

- **Why fungi?** What drew you personally to this domain rather than, say, medical imaging or autonomous driving? Was there a moment in the lab or a conversation that made fungal identification click for you?

- **What surprised you?** During dataset exploration or the first retrieval experiments, was there a result you did not expect — either encouraging or discouraging? Early surprises often shape the direction of a thesis.

- **Relationship with advisors.** How did the collaboration between Dr. Oanh (HUST, computer vision) and Prof. Duong Vu (Netherlands, fungal classification) shape the project? Did their different backgrounds create productive tension or complementary guidance?

- **Product mindset vs. research mindset.** As a self-described ICT student who loves building products, how did you balance the demands of rigorous experimentation with the instinct to ship something usable? Were there times these two mindsets conflicted?

- **What did you learn beyond the technical?** Any lessons about working with domain experts (mycologists), managing a cross-continent collaboration, or scoping a thesis project that you would pass on to the next student?

- **Constraints and trade-offs.** What was the hardest thing you had to give up or leave out of scope? Every project has a "version two" wish list — what is yours?

- **Personal growth.** How did this project change how you think about AI, product engineering, or your own career direction?
