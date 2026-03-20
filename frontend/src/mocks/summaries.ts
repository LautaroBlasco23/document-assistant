import type { SummaryOut } from '../types/api'

// Chapter 1 summaries for each document, keyed by document hash

export const mockSummaries: Record<string, SummaryOut> = {
  'a1b2c3d4e5f6': {
    chapter: 1,
    summary: `Machine learning represents a fundamental shift in how computers solve problems. Rather than following explicitly programmed instructions, machine learning systems learn from data, identifying patterns and making decisions with minimal human intervention. This chapter establishes the distinction between traditional programming — where rules are hand-crafted by engineers — and machine learning, where algorithms discover the rules themselves from examples.

The chapter introduces the three main paradigms: supervised learning, where models learn from labeled input-output pairs; unsupervised learning, where models find structure in unlabeled data; and reinforcement learning, where an agent learns by interacting with an environment and receiving feedback. Understanding these paradigms is essential because they determine which algorithms are applicable to a given problem.

Key terminology introduced includes features (the input variables), labels (the outputs in supervised settings), training data (the examples used to fit the model), and generalization (the ability to perform well on unseen examples). The quality and quantity of training data are identified as primary drivers of model performance, setting the stage for the engineering challenges explored in later chapters.`,
  },
  'd4e5f67890ab': {
    chapter: 1,
    summary: `The first chapter challenges developers and architects to reflect on what "good architecture" and "good design" actually mean. Uncle Bob argues that these concepts are not distinct — architecture refers to the high-level structural decisions that shape a system, while design covers lower-level implementation choices, but they form an unbroken continuum serving the same purpose: minimizing the effort required to build, maintain, and evolve a software system.

The central thesis is introduced through a striking observation: the best option is the one that preserves the most options. Bad architecture manifests when teams find themselves in a situation where every change feels expensive, where adding new features requires understanding and modifying vast swaths of existing code, and where the pace of delivery slows to a crawl as the system grows. This is not an inevitable consequence of complexity — it is a failure of architecture.

The chapter uses the "signature of a mess" concept to show how productivity declines over time in systems without clean architecture. Resource costs rise while throughput falls. The solution is to take architecture seriously from the beginning, keeping the cost of change low by maintaining clear separation of concerns, protecting business logic from implementation details, and ensuring the system remains easy to reason about as it grows.`,
  },
  'g7h8i9j0k1l2': {
    chapter: 1,
    summary: `"Laying Plans" opens Sun Tzu's treatise by establishing the supreme importance of calculation and strategic assessment before any conflict begins. Sun Tzu identifies five fundamental factors that determine success in war: the Moral Law (the alignment of the people with their ruler's cause), Heaven (environmental conditions like weather and season), Earth (the terrain and physical conditions of the battlefield), the Commander (the personal qualities of leadership), and Method and Discipline (the organization, logistics, and chain of command).

The chapter emphasizes that victory is decided before battle is joined. A general who performs careful calculations and fully accounts for these five factors will win; one who neglects them will be defeated. This is not mysticism — it is a rational framework for assessing comparative advantage. Sun Tzu instructs the general to compare his side and the enemy's across each factor to predict the outcome with confidence.

A defining principle introduced here is the role of deception. "All warfare is based on deception." The skillful general conceals his strengths and weaknesses, feigns weakness when strong and strength when weak, appears inactive when preparing to strike. Deception creates the conditions for attack — it is not dishonor but strategy. The chapter closes with the famous admonition that many calculations before battle lead to victory, while few lead to defeat.`,
  },
}

// Bullet-point variant summaries
export const mockBulletSummaries: Record<string, SummaryOut> = {
  'a1b2c3d4e5f6': {
    chapter: 1,
    summary: `**Key Points: What is Machine Learning?**

- Machine learning enables computers to learn from data rather than follow explicit rules
- Three main paradigms:
  - **Supervised learning**: learns from labeled input-output pairs
  - **Unsupervised learning**: finds patterns in unlabeled data
  - **Reinforcement learning**: learns via environment interaction and feedback
- Core terminology: features, labels, training data, generalization
- Data quality and quantity are the primary drivers of model performance
- Traditional programming vs. ML: rules written by humans vs. discovered from data
- Good generalization — performing well on unseen data — is the primary goal`,
  },
  'd4e5f67890ab': {
    chapter: 1,
    summary: `**Key Points: What is Design and Architecture?**

- Architecture and design are not distinct — they form a continuum
- The goal of both: **minimize the human resources required to build and maintain the system**
- "The best option is the one that preserves the most options"
- Bad architecture shows up as: slowing delivery, rising change costs, declining productivity
- The "signature of a mess": productivity falls, costs rise as system ages
- Architecture must be taken seriously from day one, not retrofitted later
- Good architecture: separates concerns, protects business logic, keeps change cost low`,
  },
  'g7h8i9j0k1l2': {
    chapter: 1,
    summary: `**Key Points: Laying Plans**

- Victory is determined by calculation before the battle begins
- Five fundamental factors that determine success:
  1. **Moral Law** — alignment of people with their leader's cause
  2. **Heaven** — weather, climate, seasons
  3. **Earth** — terrain, distances, open ground vs. narrow passes
  4. **The Commander** — wisdom, sincerity, benevolence, courage, strictness
  5. **Method and Discipline** — organization, logistics, supply lines
- Compare your side against the enemy across all five factors to predict outcome
- "All warfare is based on deception" — conceal strengths and weaknesses
- Many calculations before battle = victory; few calculations = defeat`,
  },
}
