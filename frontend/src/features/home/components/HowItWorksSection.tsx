interface WorkflowStepProps {
  number: number;
  title: string;
  description: string;
}

function WorkflowStep({ number, title, description }: WorkflowStepProps) {
  return (
    <div className="flex gap-6 items-start">
      <div className="shrink-0 w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-xl">
        {number}
      </div>
      <div>
        <h3 className="text-2xl font-semibold mb-2">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

export function HowItWorksSection() {
  const steps = [
    {
      number: 1,
      title: "Submit Content",
      description:
        "Enter a URL, video link, or GitHub repository to analyze technical content",
    },
    {
      number: 2,
      title: "Multi-Agent Analysis",
      description:
        "8 specialized agents work in parallel to extract insights, compare technologies, audit security, and plan implementation",
    },
    {
      number: 3,
      title: "Get Implementation Guide",
      description:
        "Receive a comprehensive markdown guide with code examples, best practices, and step-by-step instructions",
    },
    {
      number: 4,
      title: "Interactive Tutoring",
      description:
        "Chat with an AI tutor that uses Socratic questioning to guide your learning and implementation",
    },
  ];

  return (
    <section className="py-20 px-8">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-4xl font-bold text-center mb-16">How It Works</h2>
        <div className="space-y-8">
          {steps.map((step) => (
            <WorkflowStep key={step.number} {...step} />
          ))}
        </div>
      </div>
    </section>
  );
}
