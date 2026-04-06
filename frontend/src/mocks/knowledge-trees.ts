import type { KnowledgeTree, KnowledgeChapter, KnowledgeDocument } from '../types/knowledge-tree'

export const mockKnowledgeTrees: KnowledgeTree[] = [
  {
    id: 'tree-ml',
    title: 'Machine Learning Fundamentals',
    description: 'Core concepts, algorithms, and practical applications of ML.',
    num_chapters: 3,
    created_at: '2026-03-10T10:00:00Z',
  },
  {
    id: 'tree-clean-arch',
    title: 'Clean Architecture',
    description: 'Principles and patterns for building maintainable software systems.',
    num_chapters: 2,
    created_at: '2026-03-15T14:30:00Z',
  },
]

export const mockKnowledgeChapters: Record<string, KnowledgeChapter[]> = {
  'tree-ml': [
    { id: 'ch-ml-1', number: 1, title: 'Supervised Learning', tree_id: 'tree-ml' },
    { id: 'ch-ml-2', number: 2, title: 'Unsupervised Learning', tree_id: 'tree-ml' },
    { id: 'ch-ml-3', number: 3, title: 'Neural Networks & Deep Learning', tree_id: 'tree-ml' },
  ],
  'tree-clean-arch': [
    { id: 'ch-ca-1', number: 1, title: 'SOLID Principles', tree_id: 'tree-clean-arch' },
    { id: 'ch-ca-2', number: 2, title: 'Layered Architecture', tree_id: 'tree-clean-arch' },
  ],
}

export const mockKnowledgeDocuments: KnowledgeDocument[] = [
  // tree-ml — main doc (tree-level)
  {
    id: 'doc-ml-main',
    tree_id: 'tree-ml',
    chapter: null,
    is_main: true,
    title: 'ML Overview',
    content: `Machine Learning is a subset of Artificial Intelligence that enables systems to learn and improve from experience without being explicitly programmed.

This knowledge tree covers the foundational concepts of ML, starting from supervised learning algorithms, moving through unsupervised techniques, and concluding with neural networks and deep learning.

Key themes:
- Statistical foundations and probability theory
- Model training, evaluation, and regularization
- Practical considerations: data quality, feature engineering, overfitting`,
    created_at: '2026-03-10T10:00:00Z',
    updated_at: '2026-03-10T10:00:00Z',
  },
  // tree-ml — chapter 1 docs
  {
    id: 'doc-ml-1-linear',
    tree_id: 'tree-ml',
    chapter: 1,
    is_main: false,
    title: 'Linear Regression',
    content: `Linear regression models the relationship between a dependent variable and one or more independent variables.

The model assumes a linear relationship: y = β₀ + β₁x₁ + ... + βₙxₙ + ε

Key concepts:
- Ordinary Least Squares (OLS) estimation
- Cost function: Mean Squared Error (MSE)
- Gradient descent optimization
- Regularization: Ridge (L2) and Lasso (L1)`,
    created_at: '2026-03-10T11:00:00Z',
    updated_at: '2026-03-10T11:00:00Z',
  },
  {
    id: 'doc-ml-1-classification',
    tree_id: 'tree-ml',
    chapter: 1,
    is_main: false,
    title: 'Classification Algorithms',
    content: `Classification assigns input data to predefined categories.

Common algorithms:
- Logistic Regression: outputs probability via sigmoid function
- Decision Trees: hierarchical if-else splits on features
- Random Forests: ensemble of decision trees with bagging
- SVM: finds the hyperplane that maximizes margin between classes

Evaluation metrics: accuracy, precision, recall, F1-score, ROC-AUC`,
    created_at: '2026-03-10T11:30:00Z',
    updated_at: '2026-03-10T11:30:00Z',
  },
  // tree-ml — chapter 2 docs
  {
    id: 'doc-ml-2-clustering',
    tree_id: 'tree-ml',
    chapter: 2,
    is_main: false,
    title: 'Clustering Methods',
    content: `Unsupervised learning finds structure in unlabeled data.

K-Means Clustering:
- Assigns points to k clusters by minimizing within-cluster variance
- Sensitive to initialization; use k-means++ for better starting centroids
- Elbow method to choose k

Hierarchical Clustering:
- Agglomerative (bottom-up) or divisive (top-down)
- Dendrogram visualization shows cluster merges

DBSCAN:
- Density-based; identifies noise points
- No need to specify k in advance`,
    created_at: '2026-03-11T09:00:00Z',
    updated_at: '2026-03-11T09:00:00Z',
  },
  // tree-clean-arch — main doc
  {
    id: 'doc-ca-main',
    tree_id: 'tree-clean-arch',
    chapter: null,
    is_main: true,
    title: 'Architecture Overview',
    content: `Clean Architecture is a software design philosophy that emphasizes separation of concerns and independence of frameworks, UI, databases, and external agencies.

The central idea: business rules should not depend on implementation details. Dependencies should always point inward, toward the domain.

This knowledge tree explores the principles behind clean architecture, covering SOLID design principles and the practical application of layered architecture patterns.`,
    created_at: '2026-03-15T14:30:00Z',
    updated_at: '2026-03-15T14:30:00Z',
  },
  // tree-clean-arch — chapter 1 docs
  {
    id: 'doc-ca-1-solid',
    tree_id: 'tree-clean-arch',
    chapter: 1,
    is_main: false,
    title: 'SOLID Principles',
    content: `SOLID is an acronym for five design principles aimed at making software more maintainable and extensible.

S — Single Responsibility Principle: A class should have only one reason to change.
O — Open/Closed Principle: Open for extension, closed for modification.
L — Liskov Substitution Principle: Subtypes must be substitutable for their base types.
I — Interface Segregation Principle: Clients should not depend on interfaces they don't use.
D — Dependency Inversion Principle: Depend on abstractions, not concretions.`,
    created_at: '2026-03-15T15:00:00Z',
    updated_at: '2026-03-15T15:00:00Z',
  },
]
