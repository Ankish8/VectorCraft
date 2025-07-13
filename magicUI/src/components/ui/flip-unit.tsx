"use client";

import React from "react";
import { motion } from "framer-motion";

interface DigitCardProps {
  digit: string;
}

const DigitCard = ({ digit }: DigitCardProps) => {
  return (
    <div className="flex h-12 w-10 flex-col items-center justify-center rounded-lg bg-neutral-800 text-2xl font-bold text-white shadow-md md:h-16 md:w-12 md:text-3xl">
      {digit}
    </div>
  );
};

interface FlipUnitProps {
  digit: string;
  label?: string;
}

export const FlipUnit = ({ digit, label }: FlipUnitProps) => {
  const currentDigit = digit;
  const previousDigit = String(parseInt(digit) + 1).padStart(digit.length, "0");

  return (
    <div className="flex flex-col items-center">
      <div className="relative h-12 w-10 md:h-16 md:w-12" style={{ perspective: "300px" }}>
        <DigitCard digit={currentDigit} />

        <motion.div
          className="absolute inset-0 z-10"
          key={digit}
          initial={{ rotateX: 0 }}
          animate={{ rotateX: -90 }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
          style={{ transformOrigin: "front" }}
        >
          <DigitCard digit={previousDigit} />
        </motion.div>

        <div className="absolute top-0 left-0 h-1/2 w-full overflow-hidden">
            <DigitCard digit={currentDigit} />
        </div>
      </div>
      {label && (
        <div className="mt-2 text-xs font-medium tracking-widest text-neutral-400 uppercase">
          {label}
        </div>
      )}
    </div>
  );
};