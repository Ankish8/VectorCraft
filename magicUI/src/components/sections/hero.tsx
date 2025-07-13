"use client";

import { motion } from "framer-motion";

import { Icons } from "@/components/icons";
import HeroVideoDialog from "@/components/magicui/hero-video";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Link from "next/link";

const ease = [0.16, 1, 0.3, 1];

function HeroPriceDropBanner() {
  return (
    <motion.div
      className="mb-6 flex items-center justify-center gap-4"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease }}
    >
      <span className="rounded-md bg-red-600 px-3 py-1 text-sm font-bold text-white">
        PRICE DROP
      </span>
      <span className="text-lg text-muted-foreground">
        From <s className="text-muted-foreground/70">$295</s> - <span className="font-bold text-foreground">$39 Only</span>
      </span>
    </motion.div>
  );
}

function HeroTitles() {
  return (
    <div className="max-w-4xl mx-auto mb-8">
      <motion.h1 
        className="text-5xl md:text-7xl font-bold leading-tight mb-6 text-center"
        initial={{ filter: "blur(10px)", opacity: 0, y: 50 }}
        animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
        transition={{
          duration: 1,
          ease,
        }}
      >
        Convert <span className="aurora-text">Raster Images</span><br />
        Into <span className="aurora-text">Vector Images</span>
      </motion.h1>
      <motion.p 
        className="text-xl md:text-2xl text-gray-700 leading-relaxed max-w-3xl mx-auto text-center"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{
          delay: 0.6,
          duration: 0.8,
          ease,
        }}
      >
        Transform JPG, PNG, GIF files into crisp PDF, SVG, EPS vectors instantly with our{" "}
        <span className="line-shadow-text italic font-semibold" data-text="AI">AI</span>{" "}
        <span className="line-shadow-text italic font-semibold" data-text="powered">powered</span>{" "}
        professional conversion technology.
      </motion.p>
    </div>
  );
}

function HeroCTA() {
  return (
    <>
      <motion.div
        className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8, duration: 0.8, ease }}
      >
        <Link
          href="/buy"
          className="rainbow-button"
        >
          BUY NOW - $39
        </Link>
        <Link
          href="#testimonials"
          className="shiny-button"
        >
          Social Proof
        </Link>
      </motion.div>
      <motion.p
        className="text-sm text-muted-foreground flex items-center justify-center gap-2 mb-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.0, duration: 0.8 }}
      >
        <span className="flex items-center gap-1">
          <span className="text-green-500">●</span>
          Launch Week Special
        </span>
        <span>•</span>
        <span>One-time payment, lifetime access</span>
      </motion.p>
    </>
  );
}

function HeroImage() {
  return (
    <motion.div
      className="relative mx-auto flex w-full items-center justify-center"
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 1.2, duration: 1, ease }}
    >
      <HeroVideoDialog
        animationStyle="from-center"
        videoSrc="https://www.youtube.com/embed/qh3NGpYRG3I?si=4rb-zSdDkVK9qxxb"
        thumbnailSrc="/dashboard.png"
        thumbnailAlt="VectorCraft Demo - See Vector Conversion in Action"
        className="border rounded-lg shadow-lg max-w-screen-lg mt-16"
      />
    </motion.div>
  );
}

export default function Hero() {
  return (
    <section id="hero" className="py-20 bg-gray-50 hero-gradient" style={{ marginTop: '64px' }}>
      <div className="relative flex w-full flex-col items-center justify-start px-4 pt-16 sm:px-6 sm:pt-12 md:pt-16 lg:px-8">
        <HeroPriceDropBanner />
        <HeroTitles />
        <HeroCTA />
        <HeroImage />
        <div className="pointer-events-none absolute inset-x-0 -bottom-12 h-1/3 bg-gradient-to-t from-background via-background to-transparent lg:h-1/4"></div>
      </div>
    </section>
  );
}
