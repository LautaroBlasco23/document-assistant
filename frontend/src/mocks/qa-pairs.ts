import type { QAPairOut } from '../types/api'

// Q&A pairs for chapter 1 of each document, keyed by document hash

export const mockQAPairs: Record<string, QAPairOut[]> = {
  'a1b2c3d4e5f6': [
    {
      question: 'How does machine learning differ from traditional programming?',
      answer: 'In traditional programming, developers write explicit rules that the computer follows. In machine learning, the computer is given examples (data) and learns to identify patterns and rules on its own, without being explicitly programmed for each scenario.',
    },
    {
      question: 'What is the role of training data in machine learning?',
      answer: 'Training data is the collection of examples used to fit a machine learning model. The model adjusts its internal parameters based on this data to minimize prediction errors. The quality, quantity, and representativeness of training data directly determine how well the model will generalize to new examples.',
    },
    {
      question: 'What is supervised learning and when is it used?',
      answer: 'Supervised learning uses labeled data — pairs of inputs and their correct outputs — to train a model to make predictions. It is used when you have historical examples with known outcomes, such as classifying emails as spam or predicting house prices from features.',
    },
    {
      question: 'What problem does unsupervised learning solve?',
      answer: 'Unsupervised learning finds hidden patterns or structures in data that has no labels. It is used when you want to discover groupings, reduce dimensionality, or detect anomalies without having predefined output categories.',
    },
    {
      question: 'What is generalization, and why does it matter?',
      answer: 'Generalization is a model\'s ability to perform accurately on new, unseen data that was not part of its training set. It matters because a model that only works on training data (overfitting) has no practical value; the goal is always to build models that work well in the real world.',
    },
    {
      question: 'What is reinforcement learning and how does it differ from supervised learning?',
      answer: 'Reinforcement learning trains an agent to make sequential decisions by rewarding or penalizing its actions. Unlike supervised learning, there are no labeled examples; instead, the agent learns through trial and error, maximizing cumulative reward over time.',
    },
  ],
  'd4e5f67890ab': [
    {
      question: 'Why does Uncle Bob argue that architecture and design are not distinct concepts?',
      answer: 'Because they lie along a continuum with no clear boundary. Architecture concerns higher-level structure (module and system organization) while design handles lower-level implementation details, but both serve the same goal: minimizing the cost of building and changing the system.',
    },
    {
      question: 'What is the "signature of a mess" that Clean Architecture describes?',
      answer: 'It is the pattern where a software system\'s productivity declines over time while costs rise. As the codebase accumulates technical debt and poor structure, every change becomes more expensive and slower to deliver, eventually bringing development to a crawl.',
    },
    {
      question: 'What does the principle "the best option preserves the most options" mean?',
      answer: 'Good architecture defers decisions that do not need to be made yet, keeping all options open as long as possible. By not committing to specific frameworks, databases, or delivery mechanisms early, the system remains flexible and changeable as requirements evolve.',
    },
    {
      question: 'How can developers demonstrate the business value of clean architecture?',
      answer: 'By showing stakeholders that good architecture reduces the cost of change over time. When the system has clean separation of concerns, new features are cheaper to add, bugs are easier to find, and the team can maintain a high delivery velocity as the codebase grows.',
    },
    {
      question: 'What is the primary measure of architectural quality?',
      answer: 'The effort required to meet the needs of the customers. If that effort is low and stays low throughout the system\'s life, the architecture is good. If it grows with every new feature or change, the architecture has failed.',
    },
    {
      question: 'Why do developers often deprioritize architecture in favor of features?',
      answer: 'Because managers and stakeholders often pressure teams to deliver features quickly, and the cost of poor architecture is deferred. Architecture debt accumulates invisibly until the system becomes difficult to change, at which point the cost is much higher than if architecture had been maintained from the beginning.',
    },
  ],
  'g7h8i9j0k1l2': [
    {
      question: 'What are the five factors Sun Tzu says determine success in warfare?',
      answer: 'The Moral Law (alignment of the people with the ruler\'s cause), Heaven (environmental conditions like weather and season), Earth (terrain and physical conditions), The Commander (personal qualities: wisdom, sincerity, benevolence, courage, strictness), and Method and Discipline (organizational structure and logistics).',
    },
    {
      question: 'Why does Sun Tzu say "all warfare is based on deception"?',
      answer: 'Because strategic advantage requires the enemy to make incorrect assumptions. By concealing your true strength, intentions, and position — appearing weak when strong, inactive when active — you can create the conditions for a decisive strike that the enemy cannot anticipate or counter.',
    },
    {
      question: 'How does Sun Tzu say calculations before battle determine its outcome?',
      answer: 'The general who performs thorough calculations — comparing his side and the enemy across all five factors — will win because he has correctly assessed the balance of advantage. The one who makes few calculations and underestimates the enemy will lose. Victory is determined in the planning phase.',
    },
    {
      question: 'What does Sun Tzu mean by the Moral Law?',
      answer: 'The Moral Law is the alignment between the ruler and the people, causing them to follow him without fear for their lives. It is the motivational and psychological foundation of an army — soldiers who fight for a cause they believe in are more effective than those who fight merely under orders.',
    },
    {
      question: 'Why does Sun Tzu emphasize the commander\'s personal qualities?',
      answer: 'Because the commander\'s judgment, character, and decision-making directly determine how the other four factors are applied. Wisdom allows correct assessment, sincerity builds trust, benevolence earns loyalty, courage enables decisive action, and strictness maintains discipline.',
    },
    {
      question: 'How should a general use the concept of "appearing near when far" in practice?',
      answer: 'By using deception to mislead the enemy about your position and intentions. Feigning an attack in one direction to draw the enemy\'s attention while striking elsewhere, or concealing the speed of your advance so the enemy is unprepared when you arrive, are applications of this principle.',
    },
  ],
}
