import type { FlashcardOut } from '../types/api'

// Flashcards for chapter 1 of each document, keyed by document hash

export const mockFlashcards: Record<string, FlashcardOut[]> = {
  'a1b2c3d4e5f6': [
    {
      front: 'Machine Learning',
      back: 'A subset of AI that enables systems to learn and improve from experience without being explicitly programmed, using data to identify patterns and make decisions.',
      category: 'terminology',
    },
    {
      front: 'Training Dataset',
      back: 'The initial set of data used to train a machine learning model. It contains examples with known inputs and, for supervised learning, their corresponding correct outputs.',
      category: 'terminology',
    },
    {
      front: 'Overfitting',
      back: 'When a model learns the training data too well, including noise and random fluctuations, making it perform poorly on new, unseen data. Characterized by low training error but high test error.',
      category: 'terminology',
    },
    {
      front: 'What are the three main types of machine learning?',
      back: 'Supervised learning (uses labeled data), unsupervised learning (finds patterns in unlabeled data), and reinforcement learning (learns through rewards and penalties).',
      category: 'key_facts',
    },
    {
      front: 'What is the difference between a model and an algorithm?',
      back: 'An algorithm is the procedure for training. A model is the output after training — the mathematical representation that makes predictions.',
      category: 'key_facts',
    },
    {
      front: 'Why is data quality critical in machine learning?',
      back: 'Models learn from data, so biased, incomplete, or noisy data leads to poor predictions. High-quality, representative data is essential for models that generalize well.',
      category: 'concepts',
    },
  ],
}
