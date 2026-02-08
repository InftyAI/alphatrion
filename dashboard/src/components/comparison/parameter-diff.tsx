import { useMemo } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import type { Experiment } from '../../types';

interface ParameterDiffProps {
  experiments: Experiment[];
}

interface ParamComparison {
  key: string;
  values: (string | null)[];
  isDifferent: boolean;
}

export function ParameterDiff({ experiments }: ParameterDiffProps) {
  const paramComparisons = useMemo(() => {
    // Collect all unique parameter keys
    const allKeys = new Set<string>();
    experiments.forEach((exp) => {
      if (exp.params) {
        Object.keys(exp.params).forEach((key) => allKeys.add(key));
      }
    });

    // Compare values across experiments
    const comparisons: ParamComparison[] = Array.from(allKeys).map((key) => {
      const values = experiments.map((exp) => {
        if (exp.params && key in exp.params) {
          return JSON.stringify(exp.params[key]);
        }
        return null;
      });

      // Check if values are different
      const uniqueValues = new Set(values.filter((v) => v !== null));
      const isDifferent = uniqueValues.size > 1;

      return { key, values, isDifferent };
    });

    // Sort by different first, then alphabetically
    return comparisons.sort((a, b) => {
      if (a.isDifferent !== b.isDifferent) {
        return a.isDifferent ? -1 : 1;
      }
      return a.key.localeCompare(b.key);
    });
  }, [experiments]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Parameter Comparison</CardTitle>
        <CardDescription>
          Side-by-side comparison of experiment parameters
        </CardDescription>
      </CardHeader>
      <CardContent>
        {paramComparisons.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-muted-foreground">
            No parameters to compare
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-semibold">Parameter</TableHead>
                {experiments.map((exp, index) => (
                  <TableHead key={exp.id} className="font-semibold">
                    {exp.name}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {paramComparisons.map((param) => (
                <TableRow
                  key={param.key}
                  className={param.isDifferent ? 'bg-yellow-50 dark:bg-yellow-950' : ''}
                >
                  <TableCell className="font-medium">{param.key}</TableCell>
                  {param.values.map((value, index) => (
                    <TableCell
                      key={index}
                      className={
                        value === null
                          ? 'text-muted-foreground italic'
                          : param.isDifferent
                          ? 'font-medium'
                          : ''
                      }
                    >
                      {value === null ? '-' : value}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
