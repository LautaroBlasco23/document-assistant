import type { FlashcardOut } from '../types/api'

// Flashcards for chapter 1 of each document, keyed by document hash

export const mockFlashcards: Record<string, FlashcardOut[]> = {
  'a1b2c3d4e5f6': [
    {
      question: 'What is machine learning?',
      answer: 'Machine learning is a subset of AI that enables systems to learn and improve from experience without being explicitly programmed, using data to identify patterns and make decisions.',
    },
    {
      question: 'What are the three main types of machine learning?',
      answer: 'Supervised learning (uses labeled data), unsupervised learning (finds patterns in unlabeled data), and reinforcement learning (learns through rewards and penalties from interactions with an environment).',
    },
    {
      question: 'What is a training dataset?',
      answer: 'A training dataset is the initial set of data used to train a machine learning model. It contains examples with known inputs and, for supervised learning, their corresponding correct outputs.',
    },
    {
      question: 'What is overfitting in machine learning?',
      answer: 'Overfitting occurs when a model learns the training data too well, including noise and random fluctuations, making it perform poorly on new, unseen data. It is characterized by low training error but high test error.',
    },
    {
      question: 'What is the difference between a model and an algorithm in ML?',
      answer: 'An algorithm is the procedure or formula for training a model. A model is the output of the algorithm after it has been trained on data — it is the mathematical representation that makes predictions.',
    },
    {
      question: 'Why is data quality critical in machine learning?',
      answer: 'Models learn from data, so biased, incomplete, or noisy data leads to poor or biased predictions. High-quality, representative data is essential for building models that generalize well to real-world scenarios.',
    },
  ],
  'd4e5f67890ab': [
    {
      question: 'What is the primary goal of software architecture?',
      answer: 'To minimize the human resources required to build and maintain the system. Good architecture allows the system to be developed, deployed, and maintained with minimal effort and maximum velocity.',
    },
    {
      question: 'What is the Dependency Rule in Clean Architecture?',
      answer: 'Source code dependencies can only point inward toward higher-level policies. Code in an inner circle cannot know anything about something in an outer circle, ensuring business logic stays independent of implementation details.',
    },
    {
      question: 'What separates design from architecture?',
      answer: 'Nothing — they form a continuum. Architecture typically refers to higher-level structure (module boundaries, system components) while design covers lower-level decisions, but both serve the same goal of minimizing effort.',
    },
    {
      question: 'What does it mean for software to have "behavior"?',
      answer: 'Software must make money or save money for the stakeholders by behaving as specified. This is the first of two values software delivers (the other being structure), and it is what most developers focus on.',
    },
    {
      question: 'Why is structure more important than behavior in the long run?',
      answer: 'Behavior can be changed through patches and workarounds, but poor structure makes future changes increasingly costly. A system with good structure can be kept maintainable; one with bad structure becomes unworkable.',
    },
    {
      question: 'What does it mean for a system to be "soft"?',
      answer: 'Software must remain soft — easy to change. The difficulty of change should be proportional to the scope of the change, not to its type. This is why architecture matters: it preserves the ability to change.',
    },
  ],
  'g7h8i9j0k1l2': [
    {
      question: 'What is the foundational principle in Sun Tzu\'s Art of War?',
      answer: 'All warfare is based on deception. Strategic advantage comes from making the enemy believe something false, appearing unable when able, inactive when active, far when near.',
    },
    {
      question: 'What five factors does Sun Tzu say determine success in war?',
      answer: 'The Moral Law (unity between ruler and people), Heaven (climate, seasons), Earth (terrain), The Commander (virtues of wisdom, sincerity, benevolence, courage, strictness), and Method and Discipline (organization).',
    },
    {
      question: 'What does Sun Tzu mean by "knowing yourself and your enemy"?',
      answer: 'If you know both the enemy and yourself, you will not be imperiled in a hundred battles. Knowing yourself alone risks defeat; knowing neither leads to certain defeat. Self-awareness and intelligence are inseparable.',
    },
    {
      question: 'How does Sun Tzu define supreme military excellence?',
      answer: 'To subdue the enemy without fighting. Breaking resistance without battle is the highest form of generalship, achieved through strategy, deception, and positioning rather than direct conflict.',
    },
    {
      question: 'What role does calculation play before battle in Sun Tzu\'s thinking?',
      answer: 'The general who wins makes many calculations before the battle is fought; the one who loses makes few. Victory is determined in the temple before troops are deployed — planning is everything.',
    },
    {
      question: 'What is Sun Tzu\'s advice on speed and prolonged war?',
      answer: 'There is no instance of a nation benefiting from prolonged warfare. Speed is essential: a swift campaign may be clumsy, but a prolonged one, however skillful, has never benefited any country.',
    },
  ],
}
