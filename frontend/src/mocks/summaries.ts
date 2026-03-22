import type { SummaryOut } from '../types/api'

// Chapter 1 summaries for each document, keyed by document hash

export const mockSummaries: Record<string, SummaryOut> = {
  'a1b2c3d4e5f6': {
    chapter: 1,
    description:
      'Machine learning represents a fundamental shift in how computers solve problems. Rather than following explicitly programmed instructions, machine learning systems learn from data, identifying patterns and making decisions with minimal human intervention. The three main paradigms — supervised, unsupervised, and reinforcement learning — and core concepts such as features, labels, and generalization form the foundation explored in this chapter.',
    bullets: [
      'Machine learning enables computers to learn from data rather than follow explicit rules',
      'Three main paradigms: supervised learning, unsupervised learning, reinforcement learning',
      'Supervised learning: learns from labeled input-output pairs',
      'Unsupervised learning: finds patterns in unlabeled data',
      'Reinforcement learning: learns via environment interaction and feedback',
      'Core terminology: features, labels, training data, generalization',
      'Data quality and quantity are the primary drivers of model performance',
      'Good generalization — performing well on unseen data — is the primary goal',
    ],
  },
  'd4e5f67890ab': {
    chapter: 1,
    description:
      'The first chapter challenges developers and architects to reflect on what "good architecture" and "good design" actually mean. Uncle Bob argues they form an unbroken continuum with a single purpose: minimizing the effort required to build, maintain, and evolve a software system. The central thesis is that the best option preserves the most options, and bad architecture inevitably manifests as rising costs and slowing delivery.',
    bullets: [
      'Architecture and design are not distinct — they form a continuum',
      'The goal of both: minimize the human resources required to build and maintain the system',
      '"The best option is the one that preserves the most options"',
      'Bad architecture shows up as: slowing delivery, rising change costs, declining productivity',
      'The "signature of a mess": productivity falls, costs rise as system ages',
      'Architecture must be taken seriously from day one, not retrofitted later',
      'Good architecture: separates concerns, protects business logic, keeps change cost low',
    ],
  },
  'g7h8i9j0k1l2': {
    chapter: 1,
    description:
      '"Laying Plans" opens Sun Tzu\'s treatise by establishing the supreme importance of calculation and strategic assessment before any conflict begins. Sun Tzu identifies five fundamental factors — Moral Law, Heaven, Earth, the Commander, and Method and Discipline — that determine success in war. The chapter\'s defining insight is that victory is decided before battle is joined, and that all warfare is based on deception.',
    bullets: [
      'Victory is determined by calculation before the battle begins',
      'Five fundamental factors: Moral Law, Heaven, Earth, the Commander, Method and Discipline',
      'Moral Law: alignment of the people with their leader\'s cause',
      'Heaven: weather, climate, seasons',
      'Earth: terrain, distances, open ground vs. narrow passes',
      'The Commander: wisdom, sincerity, benevolence, courage, strictness',
      'Method and Discipline: organization, logistics, supply lines',
      'Compare your side against the enemy across all five factors to predict outcome',
      '"All warfare is based on deception" — conceal strengths and weaknesses',
      'Many calculations before battle = victory; few calculations = defeat',
    ],
  },
}
