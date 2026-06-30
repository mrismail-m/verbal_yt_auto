import React from 'react';
import { Series } from 'remotion';
import { QuestionSlide, QuestionSlideProps } from './QuestionSlide';

export type QuizProps = {
  questions: QuestionSlideProps[];
};

export const Quiz: React.FC<QuizProps> = ({ questions }) => {
  return (
    <Series>
      {questions.map((q, i) => (
        <Series.Sequence key={i} durationInFrames={210}>
          <QuestionSlide {...q} />
        </Series.Sequence>
      ))}
    </Series>
  );
};
