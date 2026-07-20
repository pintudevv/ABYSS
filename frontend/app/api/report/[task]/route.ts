import { NextRequest, NextResponse } from 'next/server';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ task: string }> }
) {
  const { task } = await params;

  if (!task) {
    return NextResponse.json({ error: 'Task ID required' }, { status: 400 });
  }

  try {
    // Backend uses /results/{task} endpoint
    const response = await fetch(`${BASE_URL}/results/${task}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: 'Report not found' }, { status: 404 });
      }
      return NextResponse.json({ error: 'Failed to fetch report' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Report fetch error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}