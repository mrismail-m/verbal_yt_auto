import "./index.css";
import { Composition } from "remotion";
import { QuestionSlide, QuestionSlideProps } from "./QuestionSlide";
import { Quiz } from "./Quiz";

const defaultProps: QuestionSlideProps = {
  question: "Doctor is to Hospital as Teacher is to ________?",
  option_a: "Classroom",
  option_b: "Market",
  option_c: "Office",
  option_d: "School",
  correct_option: "d",
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="QuestionSlide"
        component={QuestionSlide}
        durationInFrames={210} // 7 seconds at 30 fps
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
      />
      <Composition
        id="Quiz"
        component={Quiz}
        durationInFrames={210 * 15} // 7 seconds * 15 questions
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          questions: Array(15).fill(defaultProps),
        }}
      />
    </>
  );
};
