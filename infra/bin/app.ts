#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { RENTALSBACKStack } from '../lib/api-stack';

const app = new cdk.App();

// Get stage from context or default to 'dev'
const stage = app.node.tryGetContext('stage') || 'dev';

// Create stack with stage-specific configuration
new RENTALSBACKStack(app, `RENTALS-BACK-${stage.toUpperCase()}`, {
  stage: stage,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: `RENTALS-BACK infrastructure for ${stage} environment`,
  tags: {
    Project: 'RENTALS-BACK',
    Environment: stage,
    ManagedBy: 'CDK',
    Owner: 'RENTALS-TEAM'
  }
});

// Add context validation
app.node.tryGetContext('stage') || app.node.setContext('stage', 'dev');
