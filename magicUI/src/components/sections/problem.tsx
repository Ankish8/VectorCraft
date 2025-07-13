import BlurFade from "@/components/magicui/blur-fade";
import Section from "@/components/section";
import { Card, CardContent } from "@/components/ui/card";
import { Printer, CreditCard, Scissors, Shirt } from "lucide-react";

const useCases = [
  {
    title: "Professional Printing",
    description:
      "Create crisp business cards, flyers, and marketing materials that look sharp at any size. Perfect for print shops and businesses that demand quality.",
    icon: Printer,
  },
  {
    title: "Business Branding",
    description:
      "Transform your company logo into scalable vectors for websites, signs, and merchandise. Maintain brand consistency across all platforms.",
    icon: CreditCard,
  },
  {
    title: "Craft & Cutting",
    description:
      "Convert images for Cricut, Silhouette, and laser cutting machines. Create professional crafts, decals, and custom designs with precision.",
    icon: Scissors,
  },
  {
    title: "Apparel Design",
    description:
      "Prepare graphics for t-shirt printing, embroidery, and merchandise. Ensure your designs look professional on fabric and promotional items.",
    icon: Shirt,
  },
];

export default function Component() {
  return (
    <Section
      title="USE CASES"
      subtitle="See What's Possible"
      description="Real projects, real results. Here's how VectorCraft transforms your creative vision into professional reality."
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mt-12">
        {useCases.map((useCase, index) => (
          <BlurFade key={index} delay={0.2 + index * 0.2} inView>
            <Card className="bg-background border-none shadow-none">
              <CardContent className="p-6 space-y-4">
                <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                  <useCase.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="text-xl font-semibold">{useCase.title}</h3>
                <p className="text-muted-foreground">{useCase.description}</p>
              </CardContent>
            </Card>
          </BlurFade>
        ))}
      </div>
    </Section>
  );
}
