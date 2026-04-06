import type { ExamQuestion } from '../types/knowledge-tree'

// Mock exam questions for the ML knowledge tree, chapter 1 (Supervised Learning)
export const mockExamQuestions: ExamQuestion[] = [
  {
    type: 'true-false',
    id: 'tf-1',
    statement: 'Supervised learning requires labeled training data with known input-output pairs.',
    answer: true,
    explanation: 'Supervised learning learns a mapping from inputs to outputs using labeled examples. Without labels the algorithm cannot compute a supervised loss.',
  },
  {
    type: 'true-false',
    id: 'tf-2',
    statement: 'Overfitting occurs when a model performs well on new, unseen data but poorly on training data.',
    answer: false,
    explanation: 'Overfitting is the opposite: the model memorizes training data (low training error) but generalizes poorly to new examples (high test error).',
  },
  {
    type: 'multiple-choice',
    id: 'mc-1',
    question: 'Which cost function is most commonly used for linear regression?',
    choices: [
      'Cross-Entropy Loss',
      'Mean Squared Error (MSE)',
      'Hinge Loss',
      'KL Divergence',
    ],
    correctIndex: 1,
    explanation: 'MSE penalizes the squared difference between predicted and actual values, making it well-suited for continuous output regression tasks.',
  },
  {
    type: 'multiple-choice',
    id: 'mc-2',
    question: 'What does the sigmoid function output in logistic regression?',
    choices: [
      'A class label (0 or 1)',
      'The gradient of the loss',
      'A probability between 0 and 1',
      'A real-valued regression score',
    ],
    correctIndex: 2,
    explanation: 'The sigmoid squashes any real number to (0, 1), which logistic regression interprets as the probability of belonging to the positive class.',
  },
  {
    type: 'matching',
    id: 'match-1',
    prompt: 'Match each regularization technique to its description.',
    pairs: [
      { term: 'Ridge (L2)', definition: 'Penalizes the sum of squared weights, shrinks coefficients toward zero but rarely to exactly zero.' },
      { term: 'Lasso (L1)', definition: 'Penalizes the sum of absolute weights, can drive some coefficients to exactly zero (feature selection).' },
      { term: 'Dropout', definition: 'Randomly deactivates neurons during training to prevent co-adaptation in neural networks.' },
      { term: 'Early Stopping', definition: 'Halts training when validation loss stops improving to avoid overfitting.' },
    ],
  },
  {
    type: 'matching',
    id: 'match-2',
    prompt: 'Match each ML algorithm to its primary use case.',
    pairs: [
      { term: 'Linear Regression', definition: 'Predicting a continuous numeric output from one or more features.' },
      { term: 'Logistic Regression', definition: 'Binary classification outputting class probabilities.' },
      { term: 'Random Forest', definition: 'Ensemble of decision trees using bagging to improve accuracy and reduce variance.' },
      { term: 'SVM', definition: 'Finds the maximum-margin hyperplane that separates two classes.' },
    ],
  },
  {
    type: 'checkbox',
    id: 'cb-1',
    question: 'Which of the following are valid evaluation metrics for a classification model? (Select all that apply)',
    choices: [
      'Precision',
      'Mean Squared Error',
      'Recall',
      'ROC-AUC',
      'R² (R-squared)',
    ],
    correctIndices: [0, 2, 3],
    explanation: 'Precision, Recall, and ROC-AUC are classification metrics. MSE and R² are regression metrics.',
  },
  {
    type: 'checkbox',
    id: 'cb-2',
    question: 'Which statements about Decision Trees are correct? (Select all that apply)',
    choices: [
      'They are non-parametric models.',
      'They require feature scaling (normalization).',
      'They can handle both categorical and numerical features.',
      'They are immune to overfitting.',
      'They split nodes based on impurity measures like Gini or entropy.',
    ],
    correctIndices: [0, 2, 4],
    explanation: 'Decision trees are non-parametric, handle mixed feature types, and use Gini/entropy for splits. They do NOT require scaling, and they are highly prone to overfitting without pruning.',
  },
  {
    type: 'flashcard',
    id: 'fc-1',
    front: 'What is the bias-variance tradeoff?',
    back: 'Bias is error from overly simple models (underfitting); variance is error from overly complex models (overfitting). Reducing one typically increases the other — the tradeoff is finding the right model complexity.',
  },
  {
    type: 'flashcard',
    id: 'fc-2',
    front: 'What is cross-validation and why is it used?',
    back: 'Cross-validation (e.g., k-fold) splits data into k subsets, training on k-1 and validating on the remaining fold, repeated k times. It gives a more reliable estimate of model generalization than a single train/test split.',
  },
]
