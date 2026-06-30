import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import React from "react";

export type QuestionSlideProps = {
  question: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: "a" | "b" | "c" | "d";
};

const TimerCircle: React.FC<{ frame: number; fps: number; durationFrames: number }> = ({ frame, fps, durationFrames }) => {
  const progress = interpolate(frame, [0, durationFrames], [0, 1], { extrapolateRight: "clamp" });
  const timeLeft = Math.max(0, Math.ceil((durationFrames - frame) / fps));
  const dashOffset = interpolate(progress, [0, 1], [0, 283]); // 2 * pi * 45 ≈ 282.7
  
  // Quick fade out of the timer when it hits 0
  const opacity = interpolate(frame - durationFrames, [0, 10], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div className="timer-wrapper" style={{ opacity }}>
      <svg width="120" height="120" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#333" strokeWidth="6" />
        <circle 
          cx="50" 
          cy="50" 
          r="45" 
          fill="none" 
          stroke="#fff" 
          strokeWidth="6" 
          strokeDasharray="283"
          strokeDashoffset={dashOffset}
          transform="rotate(-90 50 50)"
        />
      </svg>
      <div className="timer-text">{timeLeft}</div>
    </div>
  );
};

export const QuestionSlide: React.FC<QuestionSlideProps> = ({
  question,
  option_a,
  option_b,
  option_c,
  option_d,
  correct_option,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 5 seconds * 30 fps = 150 frames for the thinking phase
  const revealFrame = 150;

  // Animations
  const titleY = interpolate(spring({ frame, fps, config: { damping: 12 } }), [0, 1], [-50, 0]);
  const titleOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const getOptionStyle = (index: number) => {
    const delay = index * 5;
    const s = spring({ frame: frame - delay, fps, config: { damping: 12 } });
    const y = interpolate(s, [0, 1], [50, 0]);
    const opacity = interpolate(frame - delay, [0, 15], [0, 1], { extrapolateRight: "clamp" });
    return {
      transform: `translateY(${y}px)`,
      opacity,
    };
  };

  const options = [
    { label: "A", text: option_a, value: "a" },
    { label: "B", text: option_b, value: "b" },
    { label: "C", text: option_c, value: "c" },
    { label: "D", text: option_d, value: "d" },
  ];

  return (
    <AbsoluteFill className="container">
      <TimerCircle frame={frame} fps={fps} durationFrames={revealFrame} />

      <h1 className="question-text" style={{ transform: `translateY(${titleY}px)`, opacity: titleOpacity }}>
        {question}
      </h1>
      
      <div className="options-container">
        {options.map((opt, i) => {
          const isCorrect = opt.value === correct_option;
          const showReveal = frame >= revealFrame;
          const isHighlighted = showReveal && isCorrect;

          const revealProgress = spring({
            frame: frame - revealFrame,
            fps,
            config: { damping: 12 },
          });

          const scale = isCorrect ? interpolate(revealProgress, [0, 1], [1, 1.05]) : 1;
          const dimmedOpacity = interpolate(revealProgress, [0, 1], [1, 0.3], { extrapolateRight: "clamp" });
          
          const baseStyle = getOptionStyle(i);
          const finalOpacity = !isCorrect && showReveal ? dimmedOpacity : baseStyle.opacity;

          return (
            <div 
              key={opt.value}
              className={`option ${isHighlighted ? "correct" : ""}`}
              style={{
                opacity: finalOpacity,
                transform: `${baseStyle.transform} scale(${scale})`,
              }}
            >
              <span className="option-label">{opt.label}</span>
              <span className="option-text">{opt.text}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
