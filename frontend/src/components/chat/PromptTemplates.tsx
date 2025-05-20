import React, { useState } from 'react';
import { Box, Typography, Button, Card, CardContent, CardActions, Alert } from '@mui/material';
import { PromptTemplate } from '../../types/index.ts'; // Your PromptTemplate type

interface PromptTemplatesProps {
  applyTemplate: (prompt: string) => void; // Function from useChat
}

const defaultTemplates: PromptTemplate[] = [
  {
    id: 'val-1',
    title: 'Company Valuation',
    description: 'Get a basic valuation analysis for a company.',
    prompt: 'Can you provide a valuation analysis for [COMPANY NAME]? Consider factors like revenue, profit margins, and industry comparisons.',
  },
  {
    id: 'fin-report-1',
    title: 'Financial Report Analysis',
    description: 'Analyze key metrics from an uploaded financial report.',
    prompt: "I've uploaded a financial report for [COMPANY NAME]. Can you analyze the key metrics, highlight important trends (YoY growth, margin changes), and identify any potential strengths or concerns?",
  },
  {
    id: 'mkt-comp-1',
    title: 'Market Comparison',
    description: 'Compare a company with its market competitors.',
    prompt: 'How does [COMPANY NAME] compare to its main competitors like [COMPETITOR 1] and [COMPETITOR 2] in terms of financial performance (e.g., revenue growth, profitability), market share, and recent strategic moves?',
  },
  {
    id: 'risk-assess-1',
    title: 'Investment Risk Assessment',
    description: 'Evaluate the risks of investing in a company.',
    prompt: 'What are the main risks associated with investing in [COMPANY NAME]? Please consider market conditions, its financial stability (liquidity, debt), industry-specific challenges, and its competitive landscape.',
  },
  {
    id: 'growth-proj-1',
    title: 'Growth Projection Inquiry',
    description: 'Inquire about growth projections based on data.',
    prompt: "Based on the historical financial data for [COMPANY NAME] (either uploaded or that we'll discuss), can you provide potential growth projections for its revenue and net income over the next 3-5 years? What are the key assumptions underpinning such projections?",
  },
  {
    id: 'cash-flow-1',
    title: 'Cash Flow Analysis',
    description: 'Analyze the cash flow statement from an uploaded document.',
    prompt: "Please analyze the cash flow statement for [COMPANY NAME] from the uploaded document. What are the main drivers of cash flow from operations, investing, and financing activities? Are there any red flags or positive signs in its cash management?",
  },
  {
    id: 'income-stmt-1',
    title: 'Income Statement Deep Dive',
    description: 'Examine trends and reasons for changes in the income statement.',
    prompt: "Let's do a deep dive into the income statement of [COMPANY NAME]. What are the significant trends in revenue, cost of goods sold, operating expenses, and net income over the past [NUMBER] years/quarters? What are the primary reasons you can infer for any substantial changes?",
  },
];


const PromptTemplates: React.FC<PromptTemplatesProps> = ({ applyTemplate }) => {
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);

  const handleUseTemplate = (template: PromptTemplate) => {
    setSelectedTemplate(template);
    applyTemplate(template.prompt);
    // Optionally, switch to the chat tab
    // This would require passing setActiveTab from ChatPage or using a global state/context
    // For now, it just populates the input. User needs to switch tabs manually.
    window.dispatchEvent(new CustomEvent('template-applied-switch-tab')); // Example event
  };

  return (
    <Box sx={{ py: 2 }}>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Select a Prompt Template
      </Typography>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 3,
        }}
      >
        {defaultTemplates.map((template) => (
          <Box
            key={template.id}
            sx={{
              flexGrow: 1,
              flexBasis: { xs: '100%', sm: 'calc(50% - 12px)', md: 'calc(33.333% - 16px)' },
              maxWidth: { xs: '100%', sm: 'calc(50% - 12px)', md: 'calc(33.333% - 16px)' },
              display: 'flex',
            }}
          >
            <Card sx={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" component="div" gutterBottom>
                  {template.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {template.description}
                </Typography>
              </CardContent>
              <CardActions sx={{ justifyContent: 'flex-start', p:2 }}>
                <Button
                  size="small"
                  variant="contained"
                  onClick={() => handleUseTemplate(template)}
                  sx={{backgroundColor: '#1976d2', '&:hover': {backgroundColor: '#1565c0'}}}
                >
                  Use Template
                </Button>
              </CardActions>
            </Card>
          </Box>
        ))}
      </Box>

      {selectedTemplate && (
        <Alert severity="info" sx={{ mt: 4 }}>
          <Typography variant="subtitle2" gutterBottom>
            Selected Template: {selectedTemplate.title}
          </Typography>
          <Typography variant="body2" sx={{ fontStyle: 'italic', mb:1 }}>
            "{selectedTemplate.prompt}"
          </Typography>
          <Typography variant="caption">
            This prompt has been copied to the chat input. You can now customize it and send your message in the "Chat" tab.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default PromptTemplates; 